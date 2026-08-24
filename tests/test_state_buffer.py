"""Strict state-buffer contract tests."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.features.network_state import FEATURE_COLUMNS
from src.streaming.state_aggregator import STATE_COLUMNS, validate_state
from src.streaming.state_buffer import StateBuffer, StateBufferError


def _states(count: int = 12, start: str = "2018-02-22 01:00:00", day: str = "2018-02-22") -> pd.DataFrame:
    rows = []
    for index, timestamp in enumerate(pd.date_range(start, periods=count, freq="10s")):
        row = {column: float(index + 1) for column in FEATURE_COLUMNS}
        row.update(timestamp=timestamp, capture_day=day)
        rows.append(row)
    return pd.DataFrame(rows)[STATE_COLUMNS]


def test_first_nine_buffer_and_tenth_inference_ready() -> None:
    buffer = StateBuffer()
    frame = _states()
    for index in range(9):
        update = buffer.push(frame.iloc[index])
        assert update.status == "buffering"
        assert update.sequence is None
    update = buffer.push(frame.iloc[9])
    assert update.status == "ready"
    assert update.sequence is not None
    assert len(update.sequence) == 10


def test_eleventh_state_rolls_window() -> None:
    buffer = StateBuffer()
    frame = _states()
    for _, row in frame.iterrows():
        update = buffer.push(row)
    assert update.status == "ready"
    assert update.sequence is not None
    assert update.sequence.iloc[0]["timestamp"] == frame.iloc[2]["timestamp"]
    assert update.sequence.iloc[-1]["timestamp"] == frame.iloc[11]["timestamp"]


def test_missing_interval_waits_without_interpolation() -> None:
    buffer = StateBuffer()
    frame = _states()
    for index in range(9):
        buffer.push(frame.iloc[index])
    gap = frame.iloc[10].copy()
    update = buffer.push(gap)
    assert update.status == "waiting_for_next_valid_state"
    assert buffer.accepted_count == 9
    assert update.sequence is None


@pytest.mark.parametrize("mutation", ["duplicate", "out_of_order"])
def test_duplicate_and_out_of_order_are_rejected(mutation: str) -> None:
    buffer = StateBuffer()
    frame = _states()
    buffer.push(frame.iloc[0])
    row = frame.iloc[0] if mutation == "duplicate" else frame.iloc[0]
    if mutation == "out_of_order":
        row = frame.iloc[0].copy()
        row["timestamp"] = frame.iloc[0]["timestamp"] - pd.Timedelta(seconds=10)
    with pytest.raises(StateBufferError):
        buffer.push(row)


def test_capture_day_boundary_resets_without_cross_day_sequence() -> None:
    buffer = StateBuffer()
    first = _states(10)
    for _, row in first.iterrows():
        buffer.push(row)
    next_day = _states(1, start="2018-02-23 01:00:00", day="2018-02-23").iloc[0]
    update = buffer.push(next_day)
    assert update.status == "day_boundary_reset"
    assert update.sequence is None
    assert buffer.capture_day == "2018-02-23"


def test_nan_and_inf_are_rejected() -> None:
    frame = _states(1)
    with pytest.raises(ValueError, match="NaN or Inf"):
        bad = frame.copy()
        bad.loc[0, "byte_sum"] = np.nan
        validate_state(bad)
    with pytest.raises(ValueError, match="NaN or Inf"):
        bad = frame.copy()
        bad.loc[0, "byte_sum"] = np.inf
        validate_state(bad)
