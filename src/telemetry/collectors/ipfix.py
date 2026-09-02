"""Explicit IPFIX extension point; no listener or template decoder yet."""

from __future__ import annotations

from typing import Any

from src.telemetry.base import TelemetryAdapter
from src.telemetry.contracts import IPFIX_CAPABILITIES, SourceType
from src.telemetry.collectors.registry import UnsupportedSourceError


class IPFIXCollector(TelemetryAdapter):
    @property
    def source_type(self) -> SourceType:
        return SourceType.IPFIX

    @property
    def capabilities(self):
        return IPFIX_CAPABILITIES

    def start(self) -> None:
        raise UnsupportedSourceError("IPFIX is an extension point; no wire listener is enabled")

    def stop(self) -> None:
        return None

    def read_event(self) -> Any | None:
        raise UnsupportedSourceError("IPFIX is not supported by this release")

    def status(self) -> dict[str, Any]:
        return {
            "adapter": "ipfix",
            "source_type": self.source_type.value,
            "source_status": IPFIX_CAPABILITIES.status.value,
            "source_capabilities": IPFIX_CAPABILITIES.as_dict(),
            "available": False,
            "started": False,
            "status": "UNSUPPORTED",
            "error": IPFIX_CAPABILITIES.notes,
        }
