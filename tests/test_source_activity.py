"""Tests for packet identity validation and deterministic source aggregation."""

from pathlib import Path

import pandas as pd
import pytest

from src.streaming.replay import iter_packet_replay_events
from src.streaming.source_activity import (
    SOURCE_ACTIVITY_COLUMNS,
    aggregate_source_activity,
    canonical_flow_5tuple,
    flow_5tuple,
)


ROOT = Path(__file__).resolve().parents[1]
MOCK = ROOT / "data" / "samples" / "source_attribution_mock.jsonl"


def _event(timestamp: str, source: str = "10.0.0.1", destination: str = "10.0.0.2", source_port: int = 1000, destination_port: int = 443, length: int = 100, flags: str = "ACK") -> dict[str, object]:
    return {
        "timestamp": timestamp,
        "source_ip": source,
        "destination_ip": destination,
        "source_port": source_port,
        "destination_port": destination_port,
        "protocol": "TCP",
        "packet_length": length,
        "tcp_flags": flags,
    }


def test_observed_and_canonical_five_tuple_handle_reverse_flow() -> None:
    forward = _event("2018-02-22T01:00:00")
    reverse = _event(
        "2018-02-22T01:00:01",
        source="10.0.0.2",
        destination="10.0.0.1",
        source_port=443,
        destination_port=1000,
    )
    assert flow_5tuple(forward) == ("10.0.0.1", "10.0.0.2", 1000, 443, "TCP")
    assert canonical_flow_5tuple(forward) == canonical_flow_5tuple(reverse)


def test_aggregation_counts_duplicate_packets_but_one_canonical_flow() -> None:
    frame = aggregate_source_activity([
        _event("2018-02-22T01:00:01"),
        _event("2018-02-22T01:00:00"),
        _event("2018-02-22T01:00:01"),
    ])
    row = frame.iloc[0]
    assert row["flow_count"] == 1
    assert row["packet_count"] == 3
    assert row["byte_count"] == 300.0
    assert row["mean_iat"] == pytest.approx(0.5)


def test_out_of_order_batch_events_are_sorted_and_boundary_isolated() -> None:
    frame = aggregate_source_activity([
        _event("2018-02-22T01:00:10", length=200),
        _event("2018-02-22T01:00:09", length=100),
    ])
    assert len(frame) == 2
    assert frame["interval_start"].tolist() == [pd.Timestamp("2018-02-22T01:00:00"), pd.Timestamp("2018-02-22T01:00:10")]


def test_empty_input_has_stable_schema() -> None:
    frame = aggregate_source_activity([])
    assert frame.empty
    assert list(frame.columns) == SOURCE_ACTIVITY_COLUMNS


def test_mock_packet_replay_is_deterministic_and_chronological() -> None:
    first = list(iter_packet_replay_events(MOCK))
    second = list(iter_packet_replay_events(MOCK))
    assert len(first) == 40
    assert [(event.timestamp, event.payload) for event in first] == [(event.timestamp, event.payload) for event in second]
    assert all(left.timestamp <= right.timestamp for left, right in zip(first, first[1:]))


@pytest.mark.parametrize(
    "bad_event",
    [
        {"timestamp": "2018-02-22T01:00:00"},
        _event("2018-02-22T01:00:00", source_port=70000),
        _event("2018-02-22T01:00:00", length=-1),
    ],
)
def test_invalid_packet_events_are_rejected(bad_event: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        aggregate_source_activity([bad_event])
