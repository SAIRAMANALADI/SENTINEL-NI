from __future__ import annotations

import numpy as np
import torch

from src.models.lstm_world_model import LSTMConfig, LSTMWorldModel, load_checkpoint, save_checkpoint, set_deterministic_seed


def test_lstm_forward_shape_and_probability_range() -> None:
    config = LSTMConfig(input_size=3, hidden_size=4, sequence_length=2, epochs=1)
    model = LSTMWorldModel(config)
    logits = model(torch.zeros((5, 2, 3), dtype=torch.float32))
    probabilities = torch.sigmoid(logits).detach().numpy()

    assert logits.shape == (5,)
    assert np.isfinite(probabilities).all()
    assert ((probabilities >= 0) & (probabilities <= 1)).all()


def test_checkpoint_reload_preserves_predictions(tmp_path) -> None:
    set_deterministic_seed(42)
    config = LSTMConfig(input_size=3, hidden_size=4, sequence_length=2, epochs=1)
    model = LSTMWorldModel(config)
    sequence = torch.arange(6, dtype=torch.float32).reshape(1, 2, 3)
    with torch.no_grad():
        before = model(sequence).numpy()
    path = tmp_path / "model.pt"
    save_checkpoint(path, model, ["f1", "f2", "f3"], "future_attack_state", "docs/TARGET_STATE_SPEC.md", "network-state-v1.0", 0.4, 1, 0.5, {})
    loaded, checkpoint = load_checkpoint(path)
    with torch.no_grad():
        after = loaded(sequence).numpy()

    assert np.allclose(before, after)
    assert checkpoint["feature_schema_version"] == "network-state-v1.0"
