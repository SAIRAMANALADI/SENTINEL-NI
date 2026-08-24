"""Tests for frozen operating-policy application in inference."""

from pathlib import Path

import pandas as pd

from src.evaluation.operating_policy import load_policy
from src.forecasting.inference import predict_network_state_sequence


ROOT = Path(__file__).resolve().parents[1]


def test_inference_uses_policy_file_and_applies_balanced_threshold() -> None:
    policy = load_policy(ROOT / "configs" / "operating_policy.yaml")
    result = predict_network_state_sequence(
        pd.read_csv(ROOT / "data" / "samples" / "inference_demo_sequence.csv")
    )
    threshold = policy["modes"][policy["primary_mode"]]["threshold"]
    assert result["operating_mode"] == policy["primary_mode"]
    assert result["threshold"] == threshold
    for row in result["forecast"]:
        assert row["warning"] is (row["score"] >= threshold)
