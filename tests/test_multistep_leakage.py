from __future__ import annotations

import numpy as np
import pandas as pd

from src.forecasting.windowing import build_multistep_sequences


def _fixture() -> pd.DataFrame:
    rows = []
    for split, day in (("train", "2018-01-01"), ("validation", "2018-01-02"), ("test", "2018-01-03")):
        for index in range(8):
            rows.append(
                {
                    "f1": float(index),
                    "f2": float(index + 1),
                    "timestamp": pd.Timestamp(day) + pd.Timedelta(seconds=index * 10),
                    "capture_day": day,
                    "split": split,
                    "binary_attack_state": index % 2,
                }
            )
    return pd.DataFrame(rows)


def test_multistep_windows_do_not_cross_days_or_splits() -> None:
    batch = build_multistep_sequences(
        _fixture(),
        ["f1", "f2"],
        "binary_attack_state",
        sequence_length=2,
        forecast_horizon=3,
    )

    assert set(zip(batch.splits, batch.groups)) <= {
        ("train", "2018-01-01"),
        ("validation", "2018-01-02"),
        ("test", "2018-01-03"),
    }
    assert np.all(batch.target_positions > batch.input_end_positions[:, None])
    assert np.all(batch.target_times > batch.origins[:, None])
    assert np.isfinite(batch.features).all()
    assert np.isfinite(batch.targets).all()


def test_future_aligned_source_column_is_rejected() -> None:
    frame = _fixture()
    frame["future_attack_state"] = frame["binary_attack_state"]
    try:
        build_multistep_sequences(frame, ["f1", "f2"], "future_attack_state", 2, 3)
    except ValueError as exc:
        assert "already +10s aligned" in str(exc)
    else:
        raise AssertionError("future_attack_state must not be shifted a second time")
