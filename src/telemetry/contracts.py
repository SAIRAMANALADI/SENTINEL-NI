"""Shared contracts for telemetry-source identity and capability reporting.

These declarations are operational metadata.  They are never model features and
do not change the frozen network-state contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class SourceType(str, Enum):
    LOCAL_PACKET_CAPTURE = "LOCAL_PACKET_CAPTURE"
    REMOTE_AGENT = "REMOTE_AGENT"
    ZEEK = "ZEEK"
    NETFLOW = "NETFLOW"
    IPFIX = "IPFIX"
    REPLAY = "REPLAY"
    MOCK = "MOCK"
    UNKNOWN = "UNKNOWN"


class SourceStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIAL = "PARTIAL"
    UNSUPPORTED = "UNSUPPORTED"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"


@dataclass(frozen=True)
class SourceCapabilities:
    """Honest source capabilities, separated into available/derivable/missing."""

    source_type: SourceType
    status: SourceStatus
    available: tuple[str, ...] = ()
    derivable: tuple[str, ...] = ()
    unavailable: tuple[str, ...] = ()
    state_compatible: bool = False
    supervised_state_compatible: bool = False
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type.value,
            "status": self.status.value,
            "available": list(self.available),
            "derivable": list(self.derivable),
            "unavailable": list(self.unavailable),
            "state_compatible": self.state_compatible,
            "supervised_state_compatible": self.supervised_state_compatible,
            "notes": self.notes,
        }


PACKET_CAPTURE_CAPABILITIES = SourceCapabilities(
    SourceType.LOCAL_PACKET_CAPTURE,
    SourceStatus.SUPPORTED,
    available=("packet_timestamp", "ip_endpoints", "transport_ports", "protocol", "packet_length", "tcp_flags", "ttl", "tcp_window", "payload_length", "fragmentation"),
    derivable=("bidirectional_flows", "flow_duration", "packet_counts", "byte_counts", "flow_iat", "packet_size_statistics", "10_second_network_state"),
    state_compatible=True,
    supervised_state_compatible=False,
    notes="Scapy/Npcap/libpcap metadata-only capture; raw packets and payloads are not retained.",
)

REMOTE_AGENT_CAPABILITIES = SourceCapabilities(
    SourceType.REMOTE_AGENT,
    SourceStatus.SUPPORTED,
    available=("approved_17_feature_state", "state_timestamp", "capture_day", "sensor_id", "telemetry_sequence"),
    derivable=(),
    unavailable=("raw_packets", "packet_payload", "packet_level_tcp_flags", "packet_level_ttl"),
    state_compatible=True,
    supervised_state_compatible=False,
    notes="Authenticated HTTPS state telemetry; packet attribution remains unavailable from aggregate state batches.",
)

REPLAY_CAPABILITIES = SourceCapabilities(
    SourceType.REPLAY,
    SourceStatus.SUPPORTED,
    available=("approved_state_or_replay_event", "event_timestamp"),
    derivable=(),
    unavailable=("live_packet_capture",),
    state_compatible=True,
    supervised_state_compatible=False,
    notes="Controlled replay/demo source using the existing validated replay loader.",
)

MOCK_CAPABILITIES = SourceCapabilities(
    SourceType.MOCK,
    SourceStatus.SUPPORTED,
    available=("test_events",),
    derivable=(),
    unavailable=("production_telemetry",),
    state_compatible=False,
    supervised_state_compatible=False,
    notes="Test/demo-only in-memory adapter; never a production telemetry source.",
)

ZEEK_CAPABILITIES = SourceCapabilities(
    SourceType.ZEEK,
    SourceStatus.PARTIAL,
    available=("event_timestamp", "ip_endpoints", "transport_ports", "protocol", "flow_duration", "packet_counts", "byte_counts", "connection_metadata"),
    derivable=("bidirectional_flow_record",),
    unavailable=("flow_iat", "tcp_flag_counts", "packet_size_statistics", "payload_size_statistics"),
    state_compatible=False,
    supervised_state_compatible=False,
    notes="conn.log parsing is implemented; conn.log alone cannot satisfy the frozen 17-feature state contract.",
)

NETFLOW_CAPABILITIES = SourceCapabilities(
    SourceType.NETFLOW,
    SourceStatus.UNSUPPORTED,
    unavailable=("collector_implementation", "validated_wire_decoder", "authenticated_ingestion", "frozen_17_feature_state"),
    notes="No NetFlow listener or decoder is enabled in this release.",
)

IPFIX_CAPABILITIES = SourceCapabilities(
    SourceType.IPFIX,
    SourceStatus.UNSUPPORTED,
    unavailable=("collector_implementation", "template_decoder", "validated_wire_decoder", "authenticated_ingestion", "frozen_17_feature_state"),
    notes="No IPFIX listener or template decoder is enabled in this release.",
)


def capabilities_for(source_type: SourceType | str) -> SourceCapabilities:
    value = SourceType(source_type)
    return {
        SourceType.LOCAL_PACKET_CAPTURE: PACKET_CAPTURE_CAPABILITIES,
        SourceType.REMOTE_AGENT: REMOTE_AGENT_CAPABILITIES,
        SourceType.REPLAY: REPLAY_CAPABILITIES,
        SourceType.MOCK: MOCK_CAPABILITIES,
        SourceType.ZEEK: ZEEK_CAPABILITIES,
        SourceType.NETFLOW: NETFLOW_CAPABILITIES,
        SourceType.IPFIX: IPFIX_CAPABILITIES,
    }.get(value, SourceCapabilities(SourceType.UNKNOWN, SourceStatus.UNSUPPORTED, notes="unknown telemetry source"))
