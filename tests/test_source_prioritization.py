"""Tests for transparent source prioritization."""

import pandas as pd

from src.streaming.source_activity import SOURCE_ACTIVITY_COLUMNS
from src.streaming.source_forecast import prioritize_sources


def _row(source: str, start: str, flow: int, packets: int, bytes_: float, destinations: int, ports: int) -> dict[str, object]:
    start_time = pd.Timestamp(start)
    return {
        "source_ip": source,
        "capture_day": "2018-02-22",
        "interval_start": start_time,
        "interval_end": start_time + pd.Timedelta(seconds=10),
        "flow_count": flow,
        "packet_count": packets,
        "byte_count": bytes_,
        "unique_destinations": destinations,
        "unique_destination_ports": ports,
        "mean_packet_size": bytes_ / max(packets, 1),
        "mean_iat": 1.0,
        "syn_count": 0,
        "ack_count": packets,
        "rst_count": 0,
        "packet_rate": packets / 10.0,
        "byte_rate": bytes_ / 10.0,
    }


def test_priorities_are_deterministic_and_include_measured_reasons() -> None:
    activity = pd.DataFrame(
        [
            _row("10.0.0.1", "2018-02-22T01:00:00", 1, 1, 100, 1, 1),
            _row("10.0.0.2", "2018-02-22T01:00:00", 1, 10, 1000, 3, 3),
            _row("10.0.0.3", "2018-02-22T01:00:00", 1, 1, 100, 1, 1),
            _row("10.0.0.3", "2018-02-22T01:00:10", 2, 10, 10000, 3, 3),
        ],
        columns=SOURCE_ACTIVITY_COLUMNS,
    )
    context = {"forecast": [{"score": 0.8, "warning": True}]}
    first = prioritize_sources(activity, context)
    second = prioritize_sources(activity, context)
    assert first.to_dict(orient="records") == second.to_dict(orient="records")
    by_source = {(row.source_ip, row.interval_start): row for row in first.itertuples()}
    assert by_source[("10.0.0.1", pd.Timestamp("2018-02-22T01:00:00"))].priority == "LOW PRIORITY SOURCE"
    assert by_source[("10.0.0.2", pd.Timestamp("2018-02-22T01:00:00"))].priority == "MEDIUM PRIORITY SOURCE"
    final = by_source[("10.0.0.3", pd.Timestamp("2018-02-22T01:00:10"))]
    assert final.priority == "HIGH PRIORITY SOURCE"
    assert "flow_count growth" in final.measured_reasons
    assert "network forecast is elevated" in final.measured_reasons
    assert final.risk_status == "candidate source"
    assert "probability" not in first.columns
