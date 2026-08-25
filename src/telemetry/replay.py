"""Replay-file telemetry adapter over the existing validated replay loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.streaming.replay import iter_replay_events
from src.telemetry.base import TelemetryAdapter


class ReplayTelemetryAdapter(TelemetryAdapter):
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._iterator = None
        self._started = False
        self._read_count = 0
        self._last_error: str | None = None

    def start(self) -> None:
        if not self.path.is_file():
            self._last_error = f"replay file does not exist: {self.path}"
            raise FileNotFoundError(self._last_error)
        self._iterator = iter(iter_replay_events(self.path))
        self._started = True

    def stop(self) -> None:
        self._started = False
        self._iterator = None

    def read_event(self) -> Any | None:
        if not self._started or self._iterator is None:
            return None
        try:
            event = next(self._iterator)
        except StopIteration:
            self._started = False
            return None
        self._read_count += 1
        return event

    def status(self) -> dict[str, Any]:
        return {
            "adapter": "replay",
            "available": self.path.is_file(),
            "started": self._started,
            "path": str(self.path),
            "read_count": self._read_count,
            "error": self._last_error,
        }

