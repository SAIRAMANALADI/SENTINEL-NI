"""Minimal telemetry adapter interface; no live packet capture implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class TelemetryAdapter(ABC):
    @abstractmethod
    def start(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def read_event(self) -> Any | None:
        raise NotImplementedError

    @abstractmethod
    def status(self) -> dict[str, Any]:
        raise NotImplementedError

