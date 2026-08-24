from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.forecasting.windowing import build_multistep_sequences


def test_k1_alignment_matches_frozen_test_rows() -> None:
    path = Path("data/processed/states/test.parquet")
    frame = pd.read_parquet(path)
    batch = build_multistep_sequences(
        frame,
        [
            "flow_count",
            "byte_sum",
            "packet_sum",
            "mean_duration",
            "median_duration",
            "mean_iat",
            "iat_std",
            "syn_flow_ratio",
            "ack_flow_ratio",
            "rst_flow_ratio",
            "fwd_byte_share",
            "fwd_packet_share",
            "unique_destination_port_count",
            "bytes_per_second",
            "packets_per_second",
            "packet_size_mean",
            "packet_size_std",
        ],
        "binary_attack_state",
        sequence_length=10,
        forecast_horizon=1,
    )
    approved = frame.iloc[batch.input_end_positions]["future_attack_state"].to_numpy()
    assert (batch.targets[:, 0] == approved).all()


def test_k1_consistency_artifact_passes_after_experiment() -> None:
    path = Path("results/multistep_metrics.json")
    if not path.exists():
        pytest.skip("multi-step experiment has not been run yet")
    result = json.loads(path.read_text(encoding="utf-8"))
    assert result["k1_alignment"]["status"] == "PASS"
    assert result["k1_alignment"]["no_second_shift"] is True
