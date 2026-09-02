"""Scapy collector behind the common source boundary."""

from __future__ import annotations

from src.telemetry.contracts import PACKET_CAPTURE_CAPABILITIES, SourceType
from src.telemetry.live import LiveTelemetryAdapter


class ScapyCollector(LiveTelemetryAdapter):
    """Compatibility-preserving name for the existing Scapy/Npcap adapter."""

    @property
    def source_type(self) -> SourceType:
        return SourceType.LOCAL_PACKET_CAPTURE

    @property
    def capabilities(self):
        return PACKET_CAPTURE_CAPABILITIES
