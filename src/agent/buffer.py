"""Bounded, crash-safe disk buffer for unsent telemetry batches."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
from typing import Any
import uuid


class BufferFullError(RuntimeError):
    """The configured local telemetry buffer cannot accept another batch."""


class BufferCorruptionError(RuntimeError):
    """A queued batch could not be decoded or validated."""


class DiskTelemetryBuffer:
    """Bounded, ordered, restart-safe queue of JSON telemetry envelopes.

    ``DROP_OLDEST`` is an explicit loss policy: an evicted envelope is removed
    from the pending queue and the eviction is exposed through ``status``.
    Partial and corrupt files are moved to ``quarantine`` rather than silently
    deleted, so a restart cannot pretend that they were delivered.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        max_batches: int = 256,
        max_bytes: int = 64 * 1024 * 1024,
        overflow_policy: str = "DROP_OLDEST",
    ) -> None:
        if max_batches <= 0 or max_bytes <= 0:
            raise ValueError("buffer limits must be positive")
        normalized_policy = overflow_policy.upper()
        if normalized_policy not in {"DROP_OLDEST", "REJECT_NEW"}:
            raise ValueError("overflow_policy must be DROP_OLDEST or REJECT_NEW")
        self.path = Path(path)
        self.max_batches = max_batches
        self.max_bytes = max_bytes
        self.overflow_policy = normalized_policy
        self.quarantine_path = self.path / "quarantine"
        self._dropped_batches = 0
        self._dropped_bytes = 0
        self._corrupt_batches = 0
        self._partial_batches = 0
        self.path.mkdir(parents=True, exist_ok=True)
        self.quarantine_path.mkdir(parents=True, exist_ok=True)
        self._quarantine_partial_files()

    def _files(self) -> list[Path]:
        return sorted(self.path.glob("batch-*.json"))

    @property
    def count(self) -> int:
        return len(self._files())

    @property
    def size_bytes(self) -> int:
        return sum(item.stat().st_size for item in self._files())

    @property
    def buffered_state_count(self) -> int:
        total = 0
        for item in self._files():
            try:
                payload = json.loads(item.read_text(encoding="utf-8"))
                total += len(payload.get("states", []))
            except (OSError, TypeError, ValueError, json.JSONDecodeError):
                continue
        return total

    @property
    def status(self) -> dict[str, Any]:
        return {
            "buffered_batches": self.count,
            "buffered_states": self.buffered_state_count,
            "buffered_bytes": self.size_bytes,
            "max_batches": self.max_batches,
            "max_bytes": self.max_bytes,
            "overflow_policy": self.overflow_policy,
            "dropped_batches": self._dropped_batches,
            "dropped_bytes": self._dropped_bytes,
            "corrupt_batches": self._corrupt_batches,
            "partial_batches": self._partial_batches,
        }

    def _quarantine(self, item: Path, *, reason: str) -> None:
        destination = self.quarantine_path / f"{reason}-{item.name}-{uuid.uuid4().hex[:8]}"
        try:
            item.replace(destination)
        except FileNotFoundError:
            return

    def _quarantine_partial_files(self) -> None:
        for item in sorted(self.path.glob(".batch-*")):
            self._quarantine(item, reason="partial")
            self._partial_batches += 1

    def _evict_oldest(self) -> None:
        files = self._files()
        if not files:
            return
        oldest = files[0]
        try:
            size = oldest.stat().st_size
        except FileNotFoundError:
            return
        oldest.unlink(missing_ok=True)
        self._dropped_batches += 1
        self._dropped_bytes += size

    def enqueue(self, payload: dict[str, Any]) -> None:
        sequence = int(payload["sequence"])
        encoded = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        destination = self.path / f"batch-{sequence:020d}.json"
        if destination.exists():
            return
        if len(encoded) > self.max_bytes:
            raise BufferFullError("telemetry batch exceeds the configured local buffer byte limit")
        while self.count >= self.max_batches or self.size_bytes + len(encoded) > self.max_bytes:
            if self.overflow_policy == "REJECT_NEW":
                raise BufferFullError("local telemetry buffer is full; new telemetry was rejected")
            before = self.count
            self._evict_oldest()
            if self.count == before:
                raise BufferFullError("local telemetry buffer could not evict its oldest batch")
        with tempfile.NamedTemporaryFile(mode="wb", dir=self.path, prefix=".batch-", delete=False) as handle:
            handle.write(encoded)
            temporary = Path(handle.name)
        temporary.replace(destination)

    def peek(self) -> dict[str, Any] | None:
        while True:
            files = self._files()
            if not files:
                return None
            item = files[0]
            try:
                payload = json.loads(item.read_text(encoding="utf-8"))
                if not isinstance(payload, dict) or int(payload.get("sequence", 0)) < 1:
                    raise BufferCorruptionError("queued telemetry envelope is invalid")
                return payload
            except (OSError, TypeError, ValueError, json.JSONDecodeError, BufferCorruptionError) as exc:
                self._quarantine(item, reason="corrupt")
                self._corrupt_batches += 1
                if isinstance(exc, BufferCorruptionError):
                    continue
                continue

    def reject(self, payload: dict[str, Any], *, reason: str, status_code: int | None = None) -> None:
        """Record a permanently rejected envelope without retrying it forever."""
        rejected = self.path / "rejected"
        rejected.mkdir(parents=True, exist_ok=True)
        record = {
            "sequence": int(payload.get("sequence", 0)),
            "sensor_id": payload.get("sensor_id"),
            "state_count": len(payload.get("states", [])),
            "status_code": status_code,
            "reason": reason[:240],
        }
        target = rejected / f"sequence-{record['sequence']:020d}.json"
        target.write_text(json.dumps(record, sort_keys=True) + "\n", encoding="utf-8")

    def pop(self, sequence: int) -> None:
        destination = self.path / f"batch-{int(sequence):020d}.json"
        destination.unlink(missing_ok=True)
