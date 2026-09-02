"""Explicit NetFlow extension point.

Wire decoding is intentionally not enabled until exporter security and a
validated protocol implementation are selected.  This class must not be
treated as a working NetFlow listener.
"""

from __future__ import annotations

from typing import Any

from src.telemetry.base import TelemetryAdapter
from src.telemetry.contracts import NETFLOW_CAPABILITIES, SourceType
from src.telemetry.collectors.registry import UnsupportedSourceError


class NetFlowCollector(TelemetryAdapter):
    @property
    def source_type(self) -> SourceType:
        return SourceType.NETFLOW

    @property
    def capabilities(self):
        return NETFLOW_CAPABILITIES

    def start(self) -> None:
        raise UnsupportedSourceError("NETFLOW is an extension point; no wire listener is enabled")

    def stop(self) -> None:
        return None

    def read_event(self) -> Any | None:
        raise UnsupportedSourceError("NETFLOW is not supported by this release")

    def status(self) -> dict[str, Any]:
        return {
            "adapter": "netflow",
            "source_type": self.source_type.value,
            "source_status": NETFLOW_CAPABILITIES.status.value,
            "source_capabilities": NETFLOW_CAPABILITIES.as_dict(),
            "available": False,
            "started": False,
            "status": "UNSUPPORTED",
            "error": NETFLOW_CAPABILITIES.notes,
        }
