"""Tests for candidate-source risk records."""

import pandas as pd

from src.evaluation.source_risk import build_source_risk_table
from src.streaming.source_activity import aggregate_source_activity


def test_source_risk_preserves_activity_and_uses_candidate_language() -> None:
    activity = aggregate_source_activity(
        [
            {
                "timestamp": "2018-02-22T01:00:00",
                "source_ip": "10.0.0.1",
                "destination_ip": "10.0.0.2",
                "source_port": 1000,
                "destination_port": 443,
                "protocol": "TCP",
                "packet_length": 100,
                "tcp_flags": "ACK",
            }
        ]
    )
    rows = build_source_risk_table(activity, {"available": True, "network_warning": False})
    assert len(rows) == 1
    assert rows[0]["source_ip"] == "10.0.0.1"
    assert rows[0]["risk_status"] == "candidate source"
    assert "probability" not in rows[0]
    assert rows[0]["activity_features"]["packet_count"] == 1
