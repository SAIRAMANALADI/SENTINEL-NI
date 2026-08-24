from __future__ import annotations

import numpy as np
import pandas as pd

from src.forecasting.windowing import build_sequences, generate_temporal_windows


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


def _state_fixture() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    groups = [
        ("train", "2018-02-14"),
        ("train", "2018-02-21"),
        ("validation", "2018-02-22"),
    ]
    value = 0
    for split, day in groups:
        for index in range(5):
            rows.append(
                {
                    "f1": value,
                    "f2": value + 100,
                    "timestamp": pd.Timestamp(day) + pd.Timedelta(seconds=index * 10),
                    "capture_day": day,
                    "split": split,
                    "future_attack_state": [1, 0, 1, 0, -1][index],
                    "future_target_available": index < 4,
                }
            )
            value += 1
    return pd.DataFrame(rows)


def test_build_sequences_preserves_pre_aligned_target_and_boundaries() -> None:
    frame = _state_fixture()
    result = build_sequences(
        frame,
        ["f1", "f2"],
        "future_attack_state",
        sequence_length=2,
        forecast_horizon=1,
    )

    assert result.features.shape == (9, 2, 2)
    assert result.targets.shape == (9,)
    assert result.report["target_alignment"] == "future_attack_state is read from the final input row; no second shift"
    assert result.report["cross_group_sequences"] is False
    assert result.targets[0] == 0
    assert result.input_end_positions[0] == result.target_positions[0]
    assert result.groups.tolist()[:3] == ["2018-02-14"] * 3
    assert result.splits.tolist()[:6] == ["train"] * 6


def test_build_sequences_horizon_and_stride_for_current_state_target() -> None:
    frame = _state_fixture().drop(columns=["future_target_available", "future_attack_state"])
    frame["current_state_target"] = np.arange(len(frame), dtype="int8") + 100
    result = build_sequences(
        frame,
        ["f1", "f2"],
        "current_state_target",
        sequence_length=2,
        forecast_horizon=2,
        stride=2,
    )

    assert result.features.shape == (3, 2, 2)
    assert result.targets[0] == 103
    assert result.target_positions[0] > result.input_end_positions[0]
    assert result.report["target_alignment"] == "target is read forecast_horizon rows after the final input row"


def test_build_sequences_empty_input_has_deterministic_shape() -> None:
    frame = _state_fixture().iloc[0:0]
    result = build_sequences(
        frame,
        ["f1", "f2"],
        "future_attack_state",
        sequence_length=3,
        forecast_horizon=1,
    )

    assert result.features.shape == (0, 3, 2)
    assert result.targets.shape == (0,)
    assert result.report["sequence_count"] == 0


def test_build_sequences_rejects_invalid_parameters_and_double_shift() -> None:
    frame = _state_fixture()
    for kwargs in (
        {"sequence_length": 0, "forecast_horizon": 1},
        {"sequence_length": 2, "forecast_horizon": 0},
        {"sequence_length": 2, "forecast_horizon": 1, "stride": 0},
        {"sequence_length": 2, "forecast_horizon": 2},
    ):
        try:
            build_sequences(frame, ["f1", "f2"], "future_attack_state", **kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError("Expected invalid window parameter failure")


def test_build_sequences_is_deterministic() -> None:
    frame = _state_fixture().sort_values(["capture_day", "timestamp"]).reset_index(drop=True)
    first = build_sequences(frame, ["f1", "f2"], "future_attack_state", sequence_length=2, forecast_horizon=1)
    second = build_sequences(frame, ["f1", "f2"], "future_attack_state", sequence_length=2, forecast_horizon=1)

    assert np.array_equal(first.features, second.features)
    assert np.array_equal(first.targets, second.targets)
    assert np.array_equal(first.groups, second.groups)
    assert np.array_equal(first.target_positions, second.target_positions)
