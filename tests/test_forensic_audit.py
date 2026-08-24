"""Adversarial, read-only probes for the SIH26-26153 forensic audit.

These tests intentionally exercise the frozen contracts with tiny fixtures. They
do not rewrite production data or train a model. Some probes document current
behavior that the audit reports as a concern (notably irregular timestamp
acceptance and stale UI test-count text).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch
from torch import nn
import yaml

from src.evaluation.feature_ablation import single_sequence_contributions
from src.evaluation.operating_policy import classify_score, load_policy
from src.features.network_state import aggregate_network_states
from src.forecasting.inference import predict_network_state_sequence
from src.forecasting.windowing import build_multistep_sequences, build_sequences
from src.models.baseline_preprocessing import BaselinePreprocessor


ROOT = Path(__file__).resolve().parents[1]
FEATURES = yaml.safe_load((ROOT / "configs/state_feature_schema.yaml").read_text(encoding="utf-8"))["FEATURE_COLUMNS"]


def _flow_fixture(labels: list[str]) -> pd.DataFrame:
    rows = []
    for index, label in enumerate(labels):
        rows.append(
            {
                "capture_date": "2018-02-28",
                "timestamp_parsed": pd.Timestamp("2018-02-28") + pd.Timedelta(seconds=index * 10),
                "Label": label,
                "Dst Port": 80 + index,
                "Flow Duration": 100.0,
                "Tot Fwd Pkts": 2.0,
                "Tot Bwd Pkts": 1.0,
                "TotLen Fwd Pkts": 20.0,
                "TotLen Bwd Pkts": 10.0,
                "Flow IAT Mean": 5.0,
                "Flow IAT Std": 1.0,
                "SYN Flag Cnt": 1.0,
                "ACK Flag Cnt": 1.0,
                "RST Flag Cnt": 0.0,
                "Pkt Len Mean": 10.0,
                "Pkt Len Std": 2.0,
            }
        )
    return pd.DataFrame(rows)


def _state_fixture() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "f1": np.arange(6, dtype="float64"),
            "timestamp": pd.date_range("2018-01-01", periods=6, freq="10s"),
            "capture_day": ["2018-01-01"] * 6,
            "binary_attack_state": [0, 1, 0, 1, 0, 1],
        }
    )


def test_target_manual_timeline_matches_next_state() -> None:
    states, _ = aggregate_network_states(_flow_fixture(["Benign", "Infilteration", "Benign", "Infilteration"]), 10)
    assert states["binary_attack_state"].tolist() == [0, 1, 0, 1]
    assert states["future_attack_state"].tolist() == [1, 0, 1, -1]
    assert states["future_target_available"].tolist() == [True, True, True, False]


def test_multistep_targets_are_exact_future_rows() -> None:
    frame = _state_fixture()
    expected = {1: [[1], [0], [1], [0], [1]], 3: [[1, 0, 1], [0, 1, 0], [1, 0, 1]], 5: [[1, 0, 1, 0, 1]]}
    for horizon, values in expected.items():
        batch = build_multistep_sequences(frame, ["f1"], "binary_attack_state", 1, horizon)
        assert batch.targets.tolist() == values
        assert batch.target_times.shape == (len(values), horizon)


def test_prealigned_target_is_not_shifted_twice() -> None:
    frame = _state_fixture()
    frame["future_attack_state"] = [1, 0, 1, 0, 1, -1]
    frame["future_target_available"] = [True, True, True, True, True, False]
    batch = build_sequences(frame, ["f1"], "future_attack_state", 2, 1)
    assert batch.targets.tolist() == [0, 1, 0, 1]
    assert batch.target_positions.tolist() == batch.input_end_positions.tolist()


def test_split_and_day_boundaries_are_isolated() -> None:
    frames = []
    for split, day in (("train", "2018-01-01"), ("validation", "2018-01-02")):
        for index in range(4):
            frames.append(
                {
                    "f1": float(index),
                    "timestamp": pd.Timestamp(day) + pd.Timedelta(seconds=index * 10),
                    "capture_day": day,
                    "split": split,
                    "future_attack_state": [1, 0, 1, -1][index],
                    "future_target_available": index < 3,
                }
            )
    batch = build_sequences(pd.DataFrame(frames), ["f1"], "future_attack_state", 2, 1)
    assert set(zip(batch.splits.tolist(), batch.groups.tolist())) == {
        ("train", "2018-01-01"),
        ("validation", "2018-01-02"),
    }
    assert batch.report["cross_group_sequences"] is False


@pytest.mark.parametrize(
    "timestamps",
    [
        [
            "2018-01-01 00:00:00",
            "2018-01-01 00:00:20",
            "2018-01-01 00:00:30",
            "2018-01-01 00:00:40",
            "2018-01-01 00:00:50",
            "2018-01-01 00:01:00",
        ],
        [
            "2018-01-01 00:00:00",
            "2018-01-01 00:00:05",
            "2018-01-01 00:00:15",
            "2018-01-01 00:00:25",
            "2018-01-01 00:00:35",
            "2018-01-01 00:00:45",
        ],
        [
            "2018-01-01 00:00:00",
            "2018-01-01 00:00:10",
            "2018-01-01 00:00:10",
            "2018-01-01 00:00:20",
            "2018-01-01 00:00:30",
            "2018-01-01 00:00:40",
        ],
        [
            "2018-01-01 00:00:10",
            "2018-01-01 00:00:00",
            "2018-01-01 00:00:20",
            "2018-01-01 00:00:30",
            "2018-01-01 00:00:40",
            "2018-01-01 00:00:50",
        ],
    ],
    ids=["20-second-gap", "5-second-gap", "duplicate", "non-monotonic"],
)
def test_invalid_cadence_is_rejected(timestamps: list[str]) -> None:
    frame = _state_fixture()
    frame["timestamp"] = pd.to_datetime(timestamps)
    with pytest.raises(ValueError, match="timestamps must be"):
        build_multistep_sequences(frame, ["f1"], "binary_attack_state", 1, 3)


def test_cross_day_rows_never_form_one_sequence() -> None:
    first = _state_fixture().iloc[:4].copy()
    second = _state_fixture().iloc[:4].copy()
    second["timestamp"] = pd.date_range("2018-01-02", periods=4, freq="10s")
    second["capture_day"] = "2018-01-02"
    frame = pd.concat([first, second], ignore_index=True)
    frame["future_attack_state"] = [1, 0, 1, -1] * 2
    frame["future_target_available"] = [True, True, True, False] * 2
    batch = build_sequences(frame, ["f1"], "future_attack_state", 2, 1)
    assert set(batch.groups.tolist()) == {"2018-01-01", "2018-01-02"}
    assert all(frame.iloc[end - 1]["capture_day"] == frame.iloc[end]["capture_day"] for end in batch.input_end_positions)


def test_schema_excludes_targets_and_has_seventeen_features() -> None:
    schema = yaml.safe_load((ROOT / "configs/state_feature_schema.yaml").read_text(encoding="utf-8"))
    forbidden = {"timestamp", "capture_day", "binary_attack_state", "future_attack_state", "future_target_available"}
    assert schema["schema_version"] == "network-state-v1.0"
    assert len(FEATURES) == 17
    assert not forbidden.intersection(FEATURES)


def test_preprocessor_does_not_refit_on_validation_or_test() -> None:
    preprocessor = BaselinePreprocessor(["f1", "f2"])
    preprocessor.fit(pd.DataFrame({"f1": [0.0, 2.0], "f2": [10.0, 12.0]}))
    mean = preprocessor.scaler.mean_.copy()
    preprocessor.transform(pd.DataFrame({"f1": [100.0], "f2": [200.0]}))
    assert np.array_equal(mean, preprocessor.scaler.mean_)
    assert preprocessor.fit_row_count == 2


def test_policy_boundary_is_inclusive_and_configured() -> None:
    policy = load_policy(ROOT / "configs/operating_policy.yaml")
    threshold = float(policy["modes"]["balanced"]["threshold"])
    assert classify_score(threshold - 1e-6, threshold) == "no_warning"
    assert classify_score(threshold, threshold) == "warning"
    assert classify_score(threshold + 1e-6, threshold) == "warning"


class _DominantFeatureModel(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.linear = nn.Linear(2, 1, bias=False)
        self.linear.weight.data = torch.tensor([[2.0, 0.1]])
        self.config = type("Config", (), {"output_size": 1})()

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        return self.linear(values[:, -1, :])


def test_explanation_follows_controlled_dominant_feature() -> None:
    explanation = single_sequence_contributions(
        _DominantFeatureModel(),
        np.array([[0.0, 0.0], [1.0, 1.0]], dtype="float32"),
        ["dominant", "minor"],
        forecast_step=1,
    )
    assert explanation["contributions"][0]["feature"] == "dominant"
    assert explanation["contributions"][0]["absolute_contribution"] > explanation["contributions"][1]["absolute_contribution"]
    assert explanation["causal_claim"] if "causal_claim" in explanation else True


def test_real_demo_inference_is_repeatable_and_rejects_contract_mutations() -> None:
    frame = pd.read_csv(ROOT / "data/samples/inference_demo_sequence.csv")
    first = predict_network_state_sequence(frame)
    second = predict_network_state_sequence(frame)
    assert first["forecast"] == second["forecast"]
    with np.errstate(invalid="ignore"):
        bad = frame.copy()
        bad["byte_sum"] = bad["byte_sum"].astype("float64")
        bad.loc[0, "byte_sum"] = np.inf
    try:
        predict_network_state_sequence(bad)
    except ValueError as exc:
        assert "NaN or Inf" in str(exc)
    else:
        raise AssertionError("infinite feature was accepted")


def test_inference_rejects_cross_date_sequence_even_when_last_row_matches() -> None:
    frame = pd.read_csv(ROOT / "data/samples/inference_demo_sequence.csv")
    frame["timestamp"] = pd.date_range("2018-02-21 23:59:10", periods=10, freq="10s").astype(str)
    frame["capture_day"] = "2018-02-22"
    with pytest.raises(ValueError, match="every timestamp"):
        predict_network_state_sequence(frame)


def test_k_specific_checkpoint_metadata_is_unambiguous() -> None:
    required = {
        "model_version",
        "forecast_horizon",
        "forecast_horizon_seconds",
        "sequence_length",
        "input_feature_count",
        "feature_schema_version",
        "target_version",
        "target_definition",
        "state_interval_seconds",
        "train_split",
        "validation_split",
        "test_split",
        "seed",
        "positive_class_weights",
        "threshold_selection_split",
        "checkpoint_selection_metric",
    }
    for horizon in (1, 3, 5):
        config = json.loads((ROOT / f"models/lstm_multistep_k{horizon}_config.json").read_text(encoding="utf-8"))
        assert required <= set(config)
        assert config["forecast_horizon"] == horizon
        assert config["forecast_horizon_seconds"] == horizon * config["state_interval_seconds"]
        assert config["input_feature_count"] == 17
        assert config["target_source_column"] == "binary_attack_state"
        checkpoint = torch.load(ROOT / f"models/lstm_multistep_k{horizon}.pt", map_location="cpu", weights_only=False)
        assert required <= set(checkpoint["model_metadata"])
        assert checkpoint["model_metadata"]["forecast_horizon"] == horizon


def test_ui_does_not_expose_a_stale_test_count() -> None:
    source = (ROOT / "app/streamlit_app.py").read_text(encoding="utf-8")
    assert "Verified locally" in source
    assert "91 tests passed" not in source
    assert "104 tests passed" not in source
