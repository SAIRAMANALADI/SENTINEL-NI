"""Tests for the stable offline inference API."""

import json
from pathlib import Path

import pandas as pd

from src.forecasting import inference
from src.forecasting.inference import predict_network_state_sequence


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "samples" / "inference_demo_sequence.csv"


def _sample() -> pd.DataFrame:
    return pd.read_csv(SAMPLE)


def test_valid_inference_returns_serializable_k5_result() -> None:
    result = predict_network_state_sequence(_sample())
    assert result["feature_schema_version"] == "network-state-v1.0"
    assert result["operating_mode"] == "balanced"
    assert result["threshold"] == 0.19
    assert result["forecast_horizon_seconds"] == 50
    assert len(result["forecast"]) == 5
    assert [row["horizon_seconds"] for row in result["forecast"]] == [10, 20, 30, 40, 50]
    assert "top_features" in result["explanation"]
    assert "temporal_positions" in result["explanation"]
    json.dumps(result)


def test_model_reload_is_deterministic_on_cpu() -> None:
    first = predict_network_state_sequence(_sample())
    second = predict_network_state_sequence(_sample())
    assert [row["score"] for row in first["forecast"]] == [row["score"] for row in second["forecast"]]
    assert [row["warning"] for row in first["forecast"]] == [row["warning"] for row in second["forecast"]]
    assert first["model_checkpoint"].endswith("models\\lstm_multistep_k5.pt") or first["model_checkpoint"].endswith("models/lstm_multistep_k5.pt")


def test_repeated_inference_reuses_validated_artifact_bundle(monkeypatch) -> None:
    inference._load_inference_bundle.cache_clear()
    original = inference.load_checkpoint
    calls = 0

    def counted_load(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(inference, "load_checkpoint", counted_load)
    predict_network_state_sequence(_sample())
    predict_network_state_sequence(_sample())

    assert calls == 1
