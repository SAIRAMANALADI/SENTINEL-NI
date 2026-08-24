from __future__ import annotations

import numpy as np
import pandas as pd

from src.forecasting.windowing import build_multistep_sequences


def _timeline() -> pd.DataFrame:
    states = [0, 0, 0, 1, 0, 1, 1, 0]
    rows = []
    for index, state in enumerate(states):
        rows.append(
            {
                "f1": float(index),
                "timestamp": pd.Timestamp("2018-01-01") + pd.Timedelta(seconds=index * 10),
                "capture_day": "2018-01-01",
                "binary_attack_state": state,
            }
        )
    return pd.DataFrame(rows)


def test_k3_reads_the_three_rows_after_the_input_end() -> None:
    frame = _timeline()
    batch = build_multistep_sequences(
        frame,
        ["f1"],
        "binary_attack_state",
        sequence_length=3,
        forecast_horizon=3,
    )

    # The first input is t0,t10,t20; its targets must be t30,t40,t50.
    assert batch.features.shape == (3, 3, 1)
    assert batch.targets.shape == (3, 3)
    assert batch.targets[0].tolist() == [1, 0, 1]
    expected_times = np.asarray(
        [
            np.datetime64("2018-01-01T00:00:30.000000000"),
            np.datetime64("2018-01-01T00:00:40.000000000"),
            np.datetime64("2018-01-01T00:00:50.000000000"),
        ],
        dtype="datetime64[ns]",
    )
    assert np.array_equal(batch.target_times[0], expected_times)


def test_k1_matches_the_approved_future_target_without_a_second_shift() -> None:
    frame = _timeline()
    frame["future_attack_state"] = frame["binary_attack_state"].shift(-1)
    frame.loc[frame.index[-1], "future_attack_state"] = 0
    batch = build_multistep_sequences(
        frame,
        ["f1"],
        "binary_attack_state",
        sequence_length=3,
        forecast_horizon=1,
    )
    approved = frame.iloc[batch.input_end_positions]["future_attack_state"].to_numpy(dtype="int8")

    assert batch.targets[:, 0].tolist() == approved.tolist()
    assert batch.report["target_alignment"] == "direct future rows at +10s increments; no second shift"
