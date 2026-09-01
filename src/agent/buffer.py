"""Bounded, crash-safe disk buffer for unsent telemetry batches."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
from typing import Any


class BufferFullError(RuntimeError):
    """The configured local telemetry buffer cannot accept another batch."""


class DiskTelemetryBuffer:
    def __init__(self, path: str | Path, *, max_batches: int = 256, max_bytes: int = 64 * 1024 * 1024) -> None:
        if max_batches <= 0 or max_bytes <= 0:
            raise ValueError("buffer limits must be positive")
        self.path = Path(path)
        self.max_batches = max_batches
        self.max_bytes = max_bytes
        self.path.mkdir(parents=True, exist_ok=True)

    def _files(self) -> list[Path]:
        return sorted(self.path.glob("batch-*.json"))

    @property
    def count(self) -> int:
        return len(self._files())

    @property
    def size_bytes(self) -> int:
        return sum(item.stat().st_size for item in self._files())

    def enqueue(self, payload: dict[str, Any]) -> None:
        sequence = int(payload["sequence"])
        encoded = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        destination = self.path / f"batch-{sequence:020d}.json"
        if destination.exists():
            return
        if self.count >= self.max_batches or self.size_bytes + len(encoded) > self.max_bytes:
            raise BufferFullError("local telemetry buffer is full; telemetry was not discarded")
        with tempfile.NamedTemporaryFile(mode="wb", dir=self.path, prefix=".batch-", delete=False) as handle:
            handle.write(encoded)
            temporary = Path(handle.name)
        temporary.replace(destination)

    def peek(self) -> dict[str, Any] | None:
        files = self._files()
        if not files:
            return None
        return json.loads(files[0].read_text(encoding="utf-8"))

    def pop(self, sequence: int) -> None:
        destination = self.path / f"batch-{int(sequence):020d}.json"
        destination.unlink(missing_ok=True)
