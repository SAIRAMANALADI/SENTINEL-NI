from __future__ import annotations

import numpy as np
import torch

from src.forecasting.multistep import DirectMultiOutputLSTM, forecast
from src.models.lstm_world_model import LSTMConfig, save_checkpoint, set_deterministic_seed


def test_direct_model_output_dimensions() -> None:
    for horizon in (1, 3, 5):
        config = LSTMConfig(input_size=17, hidden_size=4, sequence_length=10, output_size=horizon)
        model = DirectMultiOutputLSTM(config)
        logits = model(torch.zeros((2, 10, 17), dtype=torch.float32))
        expected = (2,) if horizon == 1 else (2, horizon)
        assert logits.shape == expected
        assert torch.isfinite(logits).all()


def test_direct_checkpoint_reload_and_cpu_forecast(tmp_path) -> None:
    set_deterministic_seed(42)
    config = LSTMConfig(input_size=17, hidden_size=4, sequence_length=10, output_size=3)
    model = DirectMultiOutputLSTM(config)
    path = tmp_path / "direct_k3.pt"
    save_checkpoint(
        path,
        model,
        [f"f{index}" for index in range(17)],
        "future_attack_state",
        "docs/TARGET_STATE_SPEC.md",
        "network-state-v1.0",
        0.3,
        1,
        0.5,
        {"selected_thresholds": [0.3, 0.4, 0.5]},
    )

    output = forecast(
        np.zeros((10, 17), dtype="float32"),
        horizon=3,
        checkpoint_path=path,
        reference_timestamp="2018-01-01T00:00:00",
    )
    assert len(output) == 3
    assert [item["step"] for item in output] == [1, 2, 3]
    assert [item["forecast_timestamp"] for item in output] == [
        "2018-01-01T00:00:10",
        "2018-01-01T00:00:20",
        "2018-01-01T00:00:30",
    ]
    assert all(0 <= item["prediction_probability"] <= 1 for item in output)
    assert all(item["predicted_state"] in (0, 1) for item in output)
