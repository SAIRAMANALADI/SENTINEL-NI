from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
import torch

from scripts.compare_lstm_sequence_lengths import (
    DEFAULT_RESULTS,
    RANDOM_SEED,
    SEQUENCE_LENGTHS,
    make_controlled_config,
)
from src.models.lstm_world_model import LSTMWorldModel, set_deterministic_seed


def test_controlled_configs_differ_only_by_sequence_length() -> None:
    configs = [make_controlled_config(length).to_dict() for length in SEQUENCE_LENGTHS]
    for key in configs[0]:
        if key == "sequence_length":
            continue
        assert len({config[key] for config in configs}) == 1
    assert [config["sequence_length"] for config in configs] == [5, 10, 20]


def test_experiment_seed_reproduces_model_initialization() -> None:
    config = make_controlled_config(5)
    set_deterministic_seed(RANDOM_SEED)
    first = LSTMWorldModel(config)
    first_output = first(torch.zeros((2, 5, 17), dtype=torch.float32)).detach().numpy()
    set_deterministic_seed(RANDOM_SEED)
    second = LSTMWorldModel(config)
    second_output = second(torch.zeros((2, 5, 17), dtype=torch.float32)).detach().numpy()

    assert np.allclose(first_output, second_output)
    assert all(torch.equal(first_state, second_state) for first_state, second_state in zip(first.parameters(), second.parameters()))


def test_sequence_checkpoints_load_with_matching_config() -> None:
    if not DEFAULT_RESULTS.exists():
        pytest.skip("comparison has not been run yet")
    result = json.loads(DEFAULT_RESULTS.read_text(encoding="utf-8"))
    from src.models.lstm_world_model import load_checkpoint

    for run in result["runs"]:
        model, checkpoint = load_checkpoint(run["checkpoint"])
        assert model.config.sequence_length == run["sequence_length"]
        assert checkpoint["training_metadata"]["threshold_selection_split"] == "validation"


def test_threshold_selection_is_validation_only() -> None:
    if not DEFAULT_RESULTS.exists():
        pytest.skip("comparison has not been run yet")
    result = json.loads(DEFAULT_RESULTS.read_text(encoding="utf-8"))
    assert result["controls"]["threshold_selection"] == "validation F1"
    assert result["controls"]["test_used_for_selection"] is False
    assert all(run["threshold_selection_split"] == "validation" for run in result["runs"])
    assert all(run["test_used_for_selection"] is False for run in result["runs"])
