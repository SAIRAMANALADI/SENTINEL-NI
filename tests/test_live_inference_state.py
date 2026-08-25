"""Contract tests for label-free live state generation."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.features.network_state import (
    FEATURE_COLUMNS,
    build_network_state_for_inference,
    aggregate_network_states,
)
from src.streaming.flow_builder import FlowBuilder
from src.streaming.state_aggregator import STATE_COLUMNS, aggregate_flow_window


def _packet(
    seconds: int,
    *,
    source_ip: str = "10.0.0.2",
    destination_ip: str = "10.0.0.20",
    source_port: int = 1000,
    destination_port: int = 80,
    packet_length: int = 100,
    tcp_flags: str = "",
) -> dict[str, object]:
    return {
        "timestamp": f"2018-02-22T01:00:{seconds:02d}+00:00",
        "source_ip": source_ip,
        "destination_ip": destination_ip,
        "source_port": source_port,
        "destination_port": destination_port,
        "protocol": "TCP",
        "packet_length": packet_length,
        "tcp_flags": tcp_flags,
    }


def _completed_live_flows() -> pd.DataFrame:
    builder = FlowBuilder(max_tracked_flows=10)
    records: list[dict[str, object]] = []
    for event in [
        _packet(0, tcp_flags="SYN"),
        _packet(1, source_ip="10.0.0.20", destination_ip="10.0.0.2", source_port=80, destination_port=1000, tcp_flags="ACK", packet_length=200),
        _packet(2, tcp_flags="FIN", packet_length=50),
        _packet(10, source_port=1001, tcp_flags="SYN", packet_length=120),
        _packet(11, source_ip="10.0.0.20", destination_ip="10.0.0.2", source_port=80, destination_port=1001, tcp_flags="RST", packet_length=80),
    ]:
        records.extend(builder.feed_event(event))
    records.extend(builder.flush())
    return pd.DataFrame(records)


def test_live_inference_requires_no_label_and_returns_exact_contract() -> None:
    flows = _completed_live_flows().drop(columns=["Label"], errors="ignore")
    states, report = build_network_state_for_inference(flows)

    assert list(states.columns) == STATE_COLUMNS
    assert list(states[FEATURE_COLUMNS].columns) == FEATURE_COLUMNS
    assert report["mode"] == "inference"
    assert report["target_columns"] == []
    assert not set(["Label", "binary_attack_state", "future_attack_state"]).intersection(states.columns)
    values = states[FEATURE_COLUMNS].to_numpy(dtype="float64")
    assert np.isfinite(values).all()


def test_live_state_preserves_timestamps_and_exact_ten_second_cadence() -> None:
    states, _ = build_network_state_for_inference(_completed_live_flows())
    assert states["timestamp"].tolist() == [
        pd.Timestamp("2018-02-22 01:00:00", tz="UTC"),
        pd.Timestamp("2018-02-22 01:00:10", tz="UTC"),
    ]
    assert states["capture_day"].tolist() == ["2018-02-22", "2018-02-22"]
    assert states["timestamp"].diff().iloc[1] == pd.Timedelta(seconds=10)


def test_supervised_and_inference_paths_have_identical_seventeen_features() -> None:
    flows = _completed_live_flows()
    supervised_input = flows.assign(Label=["Benign", "Infilteration"])
    inference_input = flows.drop(columns=["Label"], errors="ignore")

    supervised, _ = aggregate_network_states(supervised_input)
    inference, _ = build_network_state_for_inference(inference_input)
    pd.testing.assert_frame_equal(
        supervised[["timestamp", "capture_day", *FEATURE_COLUMNS]],
        inference[["timestamp", "capture_day", *FEATURE_COLUMNS]],
        check_exact=False,
        rtol=0.0,
        atol=1e-12,
    )


def test_streaming_window_uses_label_free_inference_path() -> None:
    flow = _completed_live_flows().iloc[[0]].drop(columns=["Label"], errors="ignore")
    state = aggregate_flow_window(flow.to_dict(orient="records"))
    assert list(state.columns) == STATE_COLUMNS
    assert "Label" not in state.columns
