from __future__ import annotations

import numpy as np
import pytest

from src.forecasting.explanation import explain_prediction
from src.forecasting.multistep import DirectMultiOutputLSTM
from src.models.lstm_world_model import LSTMConfig, save_checkpoint, set_deterministic_seed


def _checkpoint(tmp_path):
    set_deterministic_seed(42)
    config = LSTMConfig(input_size=3, hidden_size=4, sequence_length=2, output_size=1)
    model = DirectMultiOutputLSTM(config)
    path = tmp_path / "explain.pt"
    save_checkpoint(
        path,
        model,
        ["f1", "f2", "f3"],
        "future_attack_state",
        "docs/TARGET_STATE_SPEC.md",
        "network-state-v1.0",
        0.3,
        1,
        0.5,
        {},
    )
    return path


def test_explanation_schema_is_deterministic_and_cpu_safe(tmp_path) -> None:
    checkpoint = _checkpoint(tmp_path)
    sequence = np.arange(6, dtype="float32").reshape(2, 3)
    first = explain_prediction(sequence, 1, checkpoint, top_n=2)
    second = explain_prediction(sequence, 1, checkpoint, top_n=2)

    assert first == second
    assert set(first) >= {"forecast_step", "model_score", "top_features", "temporal_summary"}
    assert len(first["top_features"]) == 2
    assert first["temporal_summary"]["causal_claim"] is False


def test_explanation_rejects_empty_or_nonfinite_sequences(tmp_path) -> None:
    checkpoint = _checkpoint(tmp_path)
    with pytest.raises(ValueError):
        explain_prediction(np.empty((0, 3), dtype="float32"), 1, checkpoint)
    invalid = np.zeros((2, 3), dtype="float32")
    invalid[0, 0] = np.nan
    with pytest.raises(ValueError):
        explain_prediction(invalid, 1, checkpoint)


def test_actual_k5_explanation_checkpoint_loads_on_cpu() -> None:
    from pathlib import Path

    path = Path("models/lstm_multistep_k5.pt")
    if not path.exists():
        pytest.skip("multi-step checkpoint is not available")
    output = explain_prediction(np.zeros((10, 17), dtype="float32"), 1, path, top_n=3)
    assert output["forecast_step"] == 1
    assert len(output["top_features"]) == 3
    assert np.isfinite(output["model_score"])
