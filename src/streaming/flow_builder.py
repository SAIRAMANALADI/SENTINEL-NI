"""Deterministic packet-event to completed-flow conversion.

This adapter emits measured flow fields only. Label-free network-state
aggregation is handled by the inference-safe entry point in
``src.features.network_state``; supervised targets remain unavailable.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import pandas as pd
import yaml

from src.streaming.source_activity import normalize_packet_events


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_PATH = PROJECT_ROOT / "configs" / "live_flow_policy.yaml"

DOWNSTREAM_FLOW_FIELDS = [
    "capture_date", "timestamp_parsed", "Label", "Dst Port", "Flow Duration",
    "Tot Fwd Pkts", "Tot Bwd Pkts", "TotLen Fwd Pkts", "TotLen Bwd Pkts",
    "Flow IAT Mean", "Flow IAT Std", "SYN Flag Cnt", "ACK Flag Cnt",
    "RST Flag Cnt", "Pkt Len Mean", "Pkt Len Std",
]
AVAILABLE_FLOW_FIELDS = [field for field in DOWNSTREAM_FLOW_FIELDS if field != "Label"]


class FlowBuilderError(ValueError):
    """Base error for deterministic flow lifecycle violations."""


class FlowTableOverflowError(FlowBuilderError):
    """Raised when a new flow would exceed the configured table bound."""


@dataclass
class _Flow:
    flow_id: str
    key: tuple[str, int, str, int, str]
    forward_endpoint: tuple[str, int]
    reverse_endpoint: tuple[str, int]
    protocol: str
    first_timestamp: pd.Timestamp
    last_timestamp: pd.Timestamp
    packet_count: int = 0
    fwd_packet_count: int = 0
    bwd_packet_count: int = 0
    byte_count: int = 0
    fwd_byte_count: int = 0
    bwd_byte_count: int = 0
    syn_count: int = 0
    ack_count: int = 0
    rst_count: int = 0
    fin_seen: bool = False
    packet_lengths: list[float] | None = None
    interarrival_microseconds: list[float] | None = None

    def __post_init__(self) -> None:
        self.packet_lengths = []
        self.interarrival_microseconds = []

    def add(self, row: Mapping[str, Any]) -> None:
        timestamp = pd.Timestamp(row["timestamp"])
        if timestamp < self.last_timestamp:
            raise FlowBuilderError("flow packet timestamp moved backwards")
        if timestamp > self.last_timestamp:
            self.interarrival_microseconds.append(
                (timestamp - self.last_timestamp).total_seconds() * 1_000_000.0
            )
        self.last_timestamp = timestamp
        source_endpoint = (str(row["source_ip"]), int(row["source_port"]))
        is_forward = source_endpoint == self.forward_endpoint
        packet_length = float(row["packet_length"])
        flags = row["tcp_flags"]
        self.packet_count += 1
        self.byte_count += int(packet_length)
        self.packet_lengths.append(packet_length)
        if is_forward:
            self.fwd_packet_count += 1
            self.fwd_byte_count += int(packet_length)
        else:
            self.bwd_packet_count += 1
            self.bwd_byte_count += int(packet_length)
        self.syn_count += int("SYN" in flags)
        self.ack_count += int("ACK" in flags)
        self.rst_count += int("RST" in flags)
        self.fin_seen = self.fin_seen or "FIN" in flags

    @staticmethod
    def _std(values: list[float]) -> float:
        return float(statistics.stdev(values)) if len(values) > 1 else 0.0

    def record(self, close_reason: str) -> dict[str, Any]:
        packet_lengths = self.packet_lengths or []
        iats = self.interarrival_microseconds or []
        duration_microseconds = (self.last_timestamp - self.first_timestamp).total_seconds() * 1_000_000.0
        return {
            "flow_id": self.flow_id,
            "source_ip": self.forward_endpoint[0],
            "destination_ip": self.reverse_endpoint[0],
            "source_port": self.forward_endpoint[1],
            "destination_port": self.reverse_endpoint[1],
            "protocol": self.protocol,
            "capture_date": self.first_timestamp.strftime("%Y-%m-%d"),
            "timestamp_parsed": self.first_timestamp,
            "Dst Port": self.reverse_endpoint[1],
            "Flow Duration": duration_microseconds,
            "Tot Fwd Pkts": self.fwd_packet_count,
            "Tot Bwd Pkts": self.bwd_packet_count,
            "TotLen Fwd Pkts": self.fwd_byte_count,
            "TotLen Bwd Pkts": self.bwd_byte_count,
            "Flow IAT Mean": float(statistics.mean(iats)) if iats else 0.0,
            "Flow IAT Std": self._std(iats),
            "SYN Flag Cnt": self.syn_count,
            "ACK Flag Cnt": self.ack_count,
            "RST Flag Cnt": self.rst_count,
            "Pkt Len Mean": float(statistics.mean(packet_lengths)) if packet_lengths else 0.0,
            "Pkt Len Std": self._std(packet_lengths),
            "first_packet_timestamp": self.first_timestamp.isoformat(),
            "last_packet_timestamp": self.last_timestamp.isoformat(),
            "flow_close_reason": close_reason,
            "label_available": False,
        }


def _load_policy(path: str | Path) -> dict[str, int]:
    source = Path(path).expanduser().resolve()
    document = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("live flow policy must be a mapping")
    required = {"flow_idle_timeout_seconds", "flow_active_timeout_seconds", "max_tracked_flows"}
    missing = sorted(required.difference(document))
    if missing:
        raise ValueError(f"live flow policy is missing: {missing}")
    values: dict[str, int] = {}
    for key in required:
        value = document[key]
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{key} must be a positive integer")
        values[key] = value
    if document.get("overflow_behavior") != "reject_new_flow":
        raise ValueError("overflow_behavior must be reject_new_flow")
    return values


class FlowBuilder:
    """Build bounded bidirectional flows from normalized packet events."""

    def __init__(
        self,
        *,
        policy_path: str | Path = DEFAULT_POLICY_PATH,
        flow_idle_timeout_seconds: int | None = None,
        flow_active_timeout_seconds: int | None = None,
        max_tracked_flows: int | None = None,
    ) -> None:
        policy = _load_policy(policy_path)
        self.flow_idle_timeout_seconds = flow_idle_timeout_seconds or policy["flow_idle_timeout_seconds"]
        self.flow_active_timeout_seconds = flow_active_timeout_seconds or policy["flow_active_timeout_seconds"]
        self.max_tracked_flows = max_tracked_flows or policy["max_tracked_flows"]
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value <= 0
            for value in (self.flow_idle_timeout_seconds, self.flow_active_timeout_seconds, self.max_tracked_flows)
        ):
            raise ValueError("flow timeouts and max_tracked_flows must be positive integers")
        self._flows: dict[tuple[str, int, str, int, str], _Flow] = {}
        self._last_event_timestamp: pd.Timestamp | None = None
        self._created_count = 0
        self._closed_count = 0

    @staticmethod
    def _identity(row: Mapping[str, Any]) -> tuple[tuple[str, int, str, int, str], tuple[str, int], tuple[str, int]]:
        source = (str(row["source_ip"]), int(row["source_port"]))
        destination = (str(row["destination_ip"]), int(row["destination_port"]))
        forward, reverse = sorted((source, destination))
        protocol = str(row["protocol"]).upper()
        return (forward[0], forward[1], reverse[0], reverse[1], protocol), forward, reverse

    @staticmethod
    def _flow_id(key: tuple[str, int, str, int, str]) -> str:
        return "|".join((key[0], str(key[1]), key[2], str(key[3]), key[4]))

    def _close_due(self, timestamp: pd.Timestamp) -> list[dict[str, Any]]:
        closed: list[dict[str, Any]] = []
        for key, flow in sorted(self._flows.items(), key=lambda item: item[1].first_timestamp):
            idle_due = (timestamp - flow.last_timestamp).total_seconds() >= self.flow_idle_timeout_seconds
            active_due = (timestamp - flow.first_timestamp).total_seconds() >= self.flow_active_timeout_seconds
            if idle_due or active_due:
                closed.append(flow.record("idle_timeout" if idle_due else "active_timeout"))
                del self._flows[key]
        self._closed_count += len(closed)
        return closed

    def feed_event(self, event: Mapping[str, Any]) -> list[dict[str, Any]]:
        """Consume one event and return flows closed by this event."""

        normalized = normalize_packet_events([event])
        row = normalized.iloc[0].to_dict()
        timestamp = pd.Timestamp(row["timestamp"])
        if self._last_event_timestamp is not None and timestamp < self._last_event_timestamp:
            raise FlowBuilderError("packet events must be chronological")
        self._last_event_timestamp = timestamp
        closed = self._close_due(timestamp)
        key, forward, reverse = self._identity(row)
        flow = self._flows.get(key)
        if flow is None:
            if len(self._flows) >= self.max_tracked_flows:
                raise FlowTableOverflowError("maximum tracked flows reached; new flow rejected")
            flow = _Flow(
                flow_id=self._flow_id(key), key=key, forward_endpoint=forward,
                reverse_endpoint=reverse, protocol=key[4], first_timestamp=timestamp,
                last_timestamp=timestamp,
            )
            self._flows[key] = flow
            self._created_count += 1
        flow.add(row)
        flags = row["tcp_flags"]
        if "RST" in flags or "FIN" in flags:
            closed.append(flow.record("rst" if "RST" in flags else "fin"))
            del self._flows[key]
            self._closed_count += 1
        return closed

    def flush(self) -> list[dict[str, Any]]:
        """Close all active flows without inventing another packet."""

        closed = [flow.record("flush") for flow in sorted(self._flows.values(), key=lambda item: item.first_timestamp)]
        self._flows.clear()
        self._closed_count += len(closed)
        return closed

    def status(self) -> dict[str, Any]:
        return {
            "tracked_flows": len(self._flows), "created_flows": self._created_count,
            "closed_flows": self._closed_count,
            "last_event_timestamp": self._last_event_timestamp.isoformat() if self._last_event_timestamp else None,
            "label_available": False,
            "state_compatible": True,
            "supervised_state_compatible": False,
        }
