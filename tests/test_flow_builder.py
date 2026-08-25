"""Deterministic flow-builder contract and edge-case tests."""

from __future__ import annotations

import pytest

from src.streaming.flow_builder import FlowBuilder, FlowBuilderError, FlowTableOverflowError


def event(
    seconds: int,
    *,
    source_ip: str = "10.0.0.2",
    destination_ip: str = "10.0.0.20",
    source_port: int = 1000,
    destination_port: int = 80,
    protocol: str = "TCP",
    packet_length: int = 100,
    tcp_flags: str = "",
) -> dict[str, object]:
    return {
        "timestamp": f"2026-08-25T10:00:{seconds:02d}+00:00",
        "source_ip": source_ip,
        "destination_ip": destination_ip,
        "source_port": source_port,
        "destination_port": destination_port,
        "protocol": protocol,
        "packet_length": packet_length,
        "tcp_flags": tcp_flags,
    }


def test_bidirectional_flow_exact_statistics_and_direction() -> None:
    builder = FlowBuilder(flow_idle_timeout_seconds=30, flow_active_timeout_seconds=300, max_tracked_flows=10)
    assert builder.feed_event(event(0, packet_length=100, tcp_flags="SYN")) == []
    assert builder.feed_event(event(1, source_ip="10.0.0.20", destination_ip="10.0.0.2", source_port=80, destination_port=1000, packet_length=200, tcp_flags="ACK")) == []
    assert builder.feed_event(event(3, packet_length=50, tcp_flags="ACK")) == []
    records = builder.feed_event(event(4, packet_length=50, tcp_flags="FIN"))
    assert len(records) == 1
    record = records[0]
    assert record["source_ip"] == "10.0.0.2"
    assert record["destination_ip"] == "10.0.0.20"
    assert record["Dst Port"] == 80
    assert record["Tot Fwd Pkts"] == 3
    assert record["Tot Bwd Pkts"] == 1
    assert record["TotLen Fwd Pkts"] == 200
    assert record["TotLen Bwd Pkts"] == 200
    assert record["Flow Duration"] == pytest.approx(4_000_000)
    assert record["Flow IAT Mean"] == pytest.approx(1_333_333.3333)
    assert record["SYN Flag Cnt"] == 1
    assert record["ACK Flag Cnt"] == 2
    assert record["Pkt Len Mean"] == pytest.approx(100)
    assert record["flow_close_reason"] == "fin"
    assert "Label" not in record
    assert record["label_available"] is False


def test_one_packet_and_udp_flow_flush_without_fabrication() -> None:
    builder = FlowBuilder(max_tracked_flows=10)
    builder.feed_event(event(0, protocol="UDP", source_port=5353, destination_port=53, packet_length=64))
    record = builder.flush()[0]
    assert record["protocol"] == "UDP"
    assert record["Flow Duration"] == 0
    assert record["Flow IAT Mean"] == 0
    assert record["Pkt Len Std"] == 0
    assert record["Tot Fwd Pkts"] == 1
    assert record["Tot Bwd Pkts"] == 0


def test_rst_closes_flow() -> None:
    builder = FlowBuilder(max_tracked_flows=10)
    builder.feed_event(event(0))
    records = builder.feed_event(event(1, tcp_flags="RST"))
    assert records[0]["flow_close_reason"] == "rst"
    assert builder.status()["tracked_flows"] == 0


def test_idle_and_active_timeout_close_flows_deterministically() -> None:
    idle = FlowBuilder(flow_idle_timeout_seconds=3, flow_active_timeout_seconds=100, max_tracked_flows=10)
    idle.feed_event(event(0))
    closed = idle.feed_event(event(3, source_port=2000))
    assert closed[0]["flow_close_reason"] == "idle_timeout"

    active = FlowBuilder(flow_idle_timeout_seconds=100, flow_active_timeout_seconds=3, max_tracked_flows=10)
    active.feed_event(event(0))
    closed = active.feed_event(event(3, source_port=2000))
    assert closed[0]["flow_close_reason"] == "active_timeout"


def test_duplicate_packet_is_retained_because_no_packet_id_exists() -> None:
    builder = FlowBuilder(max_tracked_flows=10)
    packet = event(0)
    builder.feed_event(packet)
    builder.feed_event(packet)
    record = builder.flush()[0]
    assert record["Tot Fwd Pkts"] == 2


def test_out_of_order_packet_is_rejected() -> None:
    builder = FlowBuilder(max_tracked_flows=10)
    builder.feed_event(event(2))
    with pytest.raises(FlowBuilderError, match="chronological"):
        builder.feed_event(event(1))


def test_malformed_port_and_unsupported_event_are_rejected() -> None:
    builder = FlowBuilder(max_tracked_flows=10)
    with pytest.raises(ValueError, match="ports"):
        builder.feed_event(event(0, source_port=65536))
    with pytest.raises(ValueError, match="missing required fields"):
        builder.feed_event({"timestamp": "2026-08-25T10:00:00+00:00", "source_ip": "10.0.0.2"})


def test_flow_table_overflow_rejects_new_flow() -> None:
    builder = FlowBuilder(max_tracked_flows=1)
    builder.feed_event(event(0))
    with pytest.raises(FlowTableOverflowError, match="maximum tracked flows"):
        builder.feed_event(event(0, source_ip="10.0.0.3"))
