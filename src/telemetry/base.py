"""Common telemetry collector interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.telemetry.contracts import SourceCapabilities, SourceType, capabilities_for


class TelemetryAdapter(ABC):
    @property
    def source_type(self) -> SourceType:
        """Operational source identity; never used as a model feature."""

        return SourceType.UNKNOWN

    @property
    def capabilities(self) -> SourceCapabilities:
        return capabilities_for(self.source_type)

    @abstractmethod
    def start(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def read_event(self) -> Any | None:
        raise NotImplementedError

    def read_events(self, max_events: int = 1) -> list[Any]:
        """Read a bounded batch without requiring source-specific APIs."""

        if isinstance(max_events, bool) or max_events < 1:
            raise ValueError("max_events must be positive")
        events: list[Any] = []
        for _ in range(max_events):
            event = self.read_event()
            if event is None:
                break
            events.append(event)
        return events

    @abstractmethod
    def status(self) -> dict[str, Any]:
        raise NotImplementedError
