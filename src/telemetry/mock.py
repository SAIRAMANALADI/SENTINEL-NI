"""Deterministic in-memory telemetry adapter for tests and demos."""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable
from typing import Any

from src.telemetry.base import TelemetryAdapter


class MockTelemetryAdapter(TelemetryAdapter):
    def __init__(self, events: Iterable[Any] = ()) -> None:
        self._events = deque(events)
        self._started = False
        self._read_count = 0

    def start(self) -> None:
        self._started = True

    def stop(self) -> None:
        self._started = False

    def read_event(self) -> Any | None:
        if not self._started:
            return None
        if not self._events:
            return None
        self._read_count += 1
        return self._events.popleft()

    def status(self) -> dict[str, Any]:
        return {
            "adapter": "mock",
            "available": True,
            "started": self._started,
            "remaining_events": len(self._events),
            "read_count": self._read_count,
        }

