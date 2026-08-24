from __future__ import annotations

import numpy as np
import pandas as pd

from src.forecasting.windowing import generate_temporal_windows


def _fixture() -> tuple[pd.DataFrame, pd.Series, pd.Series, pd.Series]:
    features = pd.DataFrame({"f1": np.arange(9, dtype="float32"), "f2": np.arange(9, dtype="float32") + 10})
    timestamps = pd.Series(pd.date_range("2018-02-28 01:00:00", periods=9, freq="min"))
    targets = pd.Series([0, 1, 0, 1, 0, 1, 0, 1, 0], dtype="int8")
    splits = pd.Series(["train"] * 3 + ["validation"] * 3 + ["test"] * 3, dtype="string")
    return features, timestamps, targets, splits


def test_window_shape_alignment_and_split_isolation() -> None:
    result = generate_temporal_windows(*_fixture(), sequence_length=2, stride=1, forecast_horizon=1)

    assert result.report["split_isolation"] is True
    assert result.features["train"].shape == (1, 2, 2)
    assert result.features["validation"].shape == (1, 2, 2)
    assert result.features["test"].shape == (1, 2, 2)
    assert result.targets["train"].tolist() == [0]
    assert result.targets["validation"].tolist() == [1]
    assert result.targets["test"].tolist() == [0]
    assert result.origins["train"][0] < result.target_times["train"][0]
    assert result.target_positions["train"][0] > result.origin_positions["train"][0]
    assert result.report["timestamp_alignment"]["train"]["target_row_after_origin"] is True
    assert result.origins["train"][0] < result.origins["validation"][0]
    assert np.isfinite(result.features["train"]).all()


def test_window_generation_is_deterministic() -> None:
    first = generate_temporal_windows(*_fixture(), sequence_length=2, stride=1, forecast_horizon=1)
    second = generate_temporal_windows(*_fixture(), sequence_length=2, stride=1, forecast_horizon=1)

    for split in ("train", "validation", "test"):
        assert np.array_equal(first.features[split], second.features[split])
        assert np.array_equal(first.targets[split], second.targets[split])
        assert np.array_equal(first.origins[split], second.origins[split])
        assert np.array_equal(first.origin_positions[split], second.origin_positions[split])
        assert np.array_equal(first.target_positions[split], second.target_positions[split])


def test_window_rejects_nonfinite_features() -> None:
    features, timestamps, targets, splits = _fixture()
    features.loc[0, "f1"] = np.inf

    try:
        generate_temporal_windows(features, timestamps, targets, splits, sequence_length=2)
    except ValueError as exc:
        assert "non-finite" in str(exc)
    else:
        raise AssertionError("Expected non-finite feature validation failure")
