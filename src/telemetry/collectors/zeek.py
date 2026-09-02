"""Bounded Zeek ``conn.log`` reader.

The adapter accepts Zeek JSON-lines logs and the standard ``#fields`` TSV
format.  It emits normalized flow records with event time and arrival time
separate.  ``conn.log`` alone is deliberately marked PARTIAL because it does
not contain the packet IAT, TCP flag-count, and packet-size fields required by
Sentinel's frozen 17-feature state contract.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from src.telemetry.base import TelemetryAdapter
from src.telemetry.contracts import ZEEK_CAPABILITIES, SourceType


class ZeekCollectorError(ValueError):
    """A Zeek record or source configuration is invalid."""


def _event_timestamp(value: Any) -> str:
    if isinstance(value, bool):
        raise ZeekCollectorError("Zeek ts must be an epoch number or ISO timestamp")
    try:
        if isinstance(value, (int, float)):
            parsed = datetime.fromtimestamp(float(value), tz=timezone.utc)
        elif isinstance(value, str) and value.strip():
            text = value.strip()
            try:
                parsed = datetime.fromtimestamp(float(text), tz=timezone.utc)
            except ValueError:
                parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                parsed = parsed.astimezone(timezone.utc)
        else:
            raise ValueError
    except (TypeError, ValueError, OverflowError, OSError) as exc:
        raise ZeekCollectorError("Zeek ts must be a valid timestamp") from exc
    return parsed.isoformat()


def _text(value: Any, field: str, *, required: bool = True) -> str | None:
    if value in (None, "", "-"):
        if required:
            raise ZeekCollectorError(f"Zeek field is missing: {field}")
        return None
    result = str(value).strip()
    if not result and required:
        raise ZeekCollectorError(f"Zeek field is missing: {field}")
    return result or None


def _number(value: Any, field: str, *, integer: bool = False, required: bool = False) -> int | float | None:
    if value in (None, "", "-"):
        if required:
            raise ZeekCollectorError(f"Zeek field is missing: {field}")
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ZeekCollectorError(f"Zeek field is not numeric: {field}") from exc
    if number < 0:
        raise ZeekCollectorError(f"Zeek field cannot be negative: {field}")
    if integer:
        if not number.is_integer():
            raise ZeekCollectorError(f"Zeek field must be an integer: {field}")
        return int(number)
    return number


class ZeekCollector(TelemetryAdapter):
    """Read newline-terminated records from one configured Zeek conn.log."""

    def __init__(
        self,
        path: str | Path,
        *,
        sensor_id: str = "zeek-local",
        allowed_directory: str | Path | None = None,
        max_line_bytes: int = 1_048_576,
        max_seen_ids: int = 10_000,
    ) -> None:
        self.path = Path(path)
        self.sensor_id = sensor_id.strip()
        if not self.sensor_id:
            raise ValueError("sensor_id must not be empty")
        if isinstance(max_line_bytes, bool) or max_line_bytes < 256:
            raise ValueError("max_line_bytes must be at least 256")
        if isinstance(max_seen_ids, bool) or max_seen_ids < 1:
            raise ValueError("max_seen_ids must be positive")
        if allowed_directory is not None:
            root = Path(allowed_directory).resolve()
            candidate = self.path.resolve()
            try:
                candidate.relative_to(root)
            except ValueError as exc:
                raise ValueError("Zeek path must stay inside allowed_directory") from exc
        self.max_line_bytes = max_line_bytes
        self._started = False
        self._offset = 0
        self._file_identity: tuple[int, int] | None = None
        self._fields: list[str] | None = None
        self._seen_ids: set[str] = set()
        self._seen_order: deque[str] = deque(maxlen=max_seen_ids)
        self._read_count = 0
        self._invalid_count = 0
        self._duplicate_count = 0
        self._late_count = 0
        self._rotation_count = 0
        self._last_event_timestamp: str | None = None
        self._last_arrival_timestamp: str | None = None
        self._last_error: str | None = None

    @property
    def source_type(self) -> SourceType:
        return SourceType.ZEEK

    @property
    def capabilities(self):
        return ZEEK_CAPABILITIES

    def start(self) -> None:
        if not self.path.is_file():
            self._last_error = f"Zeek log does not exist: {self.path}"
            raise FileNotFoundError(self._last_error)
        self._started = True
        self._last_error = None
        self._sync_file_identity()

    def stop(self) -> None:
        self._started = False

    def _sync_file_identity(self) -> None:
        try:
            stat = self.path.stat()
        except OSError as exc:
            raise FileNotFoundError(f"Zeek log cannot be read: {self.path}") from exc
        identity = (int(stat.st_dev), int(stat.st_ino))
        if self._file_identity is None:
            self._file_identity = identity
        elif identity != self._file_identity or stat.st_size < self._offset:
            self._offset = 0
            self._fields = None
            self._file_identity = identity
            self._rotation_count += 1

    def _read_line(self) -> str | None:
        self._sync_file_identity()
        try:
            with self.path.open("r", encoding="utf-8", errors="strict", newline="") as handle:
                handle.seek(self._offset)
                line = handle.readline(self.max_line_bytes + 1)
                if not line:
                    return None
                if not line.endswith("\n"):
                    if len(line) > self.max_line_bytes:
                        self._last_error = "Zeek record exceeds max_line_bytes"
                        # Consume the remainder of this line without retaining it.
                        while handle.readline(self.max_line_bytes + 1):
                            pass
                        self._offset = handle.tell()
                        self._invalid_count += 1
                        return ""
                    return None  # partial write; retry from the same offset
                self._offset = handle.tell()
                return line.rstrip("\r\n")
        except UnicodeError as exc:
            self._invalid_count += 1
            self._last_error = "Zeek log contains invalid UTF-8"
            return ""
        except OSError as exc:
            self._last_error = str(exc)
            return None

    def _decode_line(self, line: str) -> Mapping[str, Any] | None:
        if not line or line.startswith("#"):
            if line.startswith("#fields"):
                fields = line.split("\t")[1:]
                if not fields:
                    raise ZeekCollectorError("Zeek #fields header is empty")
                self._fields = fields
            return None
        if line.lstrip().startswith("{"):
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ZeekCollectorError("Zeek JSON record must be an object")
            return value
        if self._fields is None:
            raise ZeekCollectorError("Zeek TSV data requires a preceding #fields header")
        values = line.split("\t")
        if len(values) != len(self._fields):
            raise ZeekCollectorError("Zeek TSV field count does not match #fields")
        return dict(zip(self._fields, values))

    def _normalize(self, record: Mapping[str, Any], raw_line: str) -> dict[str, Any]:
        timestamp = _event_timestamp(record.get("ts"))
        source_ip = _text(record.get("id.orig_h"), "id.orig_h")
        destination_ip = _text(record.get("id.resp_h"), "id.resp_h")
        source_port = _number(record.get("id.orig_p"), "id.orig_p", integer=True, required=True)
        destination_port = _number(record.get("id.resp_p"), "id.resp_p", integer=True, required=True)
        assert source_ip is not None and destination_ip is not None and isinstance(source_port, int) and isinstance(destination_port, int)
        if source_port > 65535 or destination_port > 65535:
            raise ZeekCollectorError("Zeek port is outside 0..65535")
        protocol = _text(record.get("proto"), "proto")
        assert protocol is not None
        record_id = _text(record.get("uid"), "uid", required=False) or hashlib.sha256(raw_line.encode("utf-8")).hexdigest()
        arrival = datetime.now(timezone.utc).isoformat()
        if self._last_event_timestamp is not None and timestamp < self._last_event_timestamp:
            self._late_count += 1
        self._last_event_timestamp = max(timestamp, self._last_event_timestamp or timestamp)
        self._last_arrival_timestamp = arrival
        normalized: dict[str, Any] = {
            "timestamp": timestamp,
            "event_timestamp": timestamp,
            "arrival_timestamp": arrival,
            "sensor_id": self.sensor_id,
            "source_type": self.source_type.value,
            "record_id": record_id,
            "source_ip": source_ip,
            "destination_ip": destination_ip,
            "source_port": source_port,
            "destination_port": destination_port,
            "protocol": protocol.upper(),
        }
        for output, field, integer in (
            ("flow_duration", "duration", False),
            ("forward_bytes", "orig_bytes", True),
            ("reverse_bytes", "resp_bytes", True),
            ("forward_packets", "orig_pkts", True),
            ("reverse_packets", "resp_pkts", True),
        ):
            normalized[output] = _number(record.get(field), field, integer=integer)
        for field in ("conn_state", "local_orig", "local_resp"):
            value = _text(record.get(field), field, required=False)
            if value is not None:
                normalized[field] = value
        return normalized

    def read_event(self) -> dict[str, Any] | None:
        if not self._started:
            return None
        while True:
            line = self._read_line()
            if line is None:
                return None
            try:
                record = self._decode_line(line)
                if record is None:
                    continue
                event = self._normalize(record, line)
            except (ZeekCollectorError, json.JSONDecodeError, TypeError, ValueError) as exc:
                self._invalid_count += 1
                self._last_error = str(exc)
                continue
            record_id = str(event["record_id"])
            if record_id in self._seen_ids:
                self._duplicate_count += 1
                continue
            if len(self._seen_order) == self._seen_order.maxlen:
                self._seen_ids.discard(self._seen_order.popleft())
            self._seen_order.append(record_id)
            self._seen_ids.add(record_id)
            self._read_count += 1
            return event

    def status(self) -> dict[str, Any]:
        configured = self.path.is_file()
        status = "ZEEK_RUNNING" if self._started else "ZEEK_STOPPED"
        if self._last_error and not configured:
            status = "ZEEK_DEGRADED"
        return {
            "adapter": "zeek-conn-log",
            "source_type": self.source_type.value,
            "source_status": "CONFIGURATION_ERROR" if not configured else self.capabilities.status.value,
            "source_capabilities": self.capabilities.as_dict(),
            "available": configured,
            "started": self._started,
            "status": status,
            "path": str(self.path),
            "read_count": self._read_count,
            "invalid_count": self._invalid_count,
            "duplicate_count": self._duplicate_count,
            "late_event_count": self._late_count,
            "rotation_count": self._rotation_count,
            "last_event": self._last_event_timestamp,
            "last_telemetry": self._last_arrival_timestamp,
            "error": self._last_error,
        }
