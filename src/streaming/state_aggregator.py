"""Streaming adapters for the frozen 10-second network-state contract.

This module deliberately delegates flow-level arithmetic to the existing
``src.features.network_state.aggregate_network_states`` implementation. It
does not define a second feature schema or target rule.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import numpy as np
import pandas as pd

from src.features.network_state import (
    FEATURE_COLUMNS,
    REQUIRED_COLUMNS,
    aggregate_network_states,
)


STATE_CONTEXT_COLUMNS = ["timestamp", "capture_day"]
STATE_COLUMNS = FEATURE_COLUMNS + STATE_CONTEXT_COLUMNS
DEFAULT_INTERVAL_SECONDS = 10


def _ensure_state_columns(frame: pd.DataFrame) -> pd.DataFrame:
    if list(frame.columns) != STATE_COLUMNS:
        missing = [column for column in STATE_COLUMNS if column not in frame.columns]
        unexpected = [column for column in frame.columns if column not in STATE_COLUMNS]
        if missing:
            raise ValueError(f"state is missing required columns: {missing}")
        if unexpected:
            raise ValueError(f"state contains unsupported columns: {unexpected}")
        raise ValueError("state column order does not match the frozen contract")
    if frame.empty:
        raise ValueError("state frame must contain at least one state")

    result = frame.copy()
    result["timestamp"] = pd.to_datetime(result["timestamp"], errors="coerce", format="mixed")
    if result["timestamp"].isna().any():
        raise ValueError("state contains invalid timestamps")
    result["capture_day"] = result["capture_day"].astype("string")
    if result["capture_day"].isna().any():
        raise ValueError("state contains a missing capture_day")
    if result["timestamp"].dt.strftime("%Y-%m-%d").ne(result["capture_day"]).any():
        raise ValueError("state timestamps must belong to capture_day")

    for column in FEATURE_COLUMNS:
        if pd.api.types.is_bool_dtype(result[column]):
            raise TypeError(f"state feature {column!r} must be numeric")
        result[column] = pd.to_numeric(result[column], errors="coerce")
        if not pd.api.types.is_numeric_dtype(result[column]):
            raise TypeError(f"state feature {column!r} must be numeric")
    values = result[FEATURE_COLUMNS].to_numpy(dtype="float64")
    if not np.isfinite(values).all():
        raise ValueError("state features contain NaN or Inf")
    return result[STATE_COLUMNS].reset_index(drop=True)


def validate_state(state: Mapping[str, Any] | pd.Series | pd.DataFrame) -> pd.DataFrame:
    """Validate one state or a state frame against the exact inference input schema."""

    if isinstance(state, pd.Series):
        frame = state.to_frame().T
    elif isinstance(state, Mapping):
        frame = pd.DataFrame([dict(state)])
    elif isinstance(state, pd.DataFrame):
        frame = state
    else:
        raise TypeError("state must be a mapping, pandas Series, or pandas DataFrame")
    return _ensure_state_columns(frame)


def aggregate_flow_window(
    events: Iterable[Mapping[str, Any] | pd.Series],
    *,
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
) -> pd.DataFrame:
    """Aggregate raw flow events from one completed 10-second window.

    The returned frame contains exactly the 17 frozen model features followed
    by ``timestamp`` and ``capture_day``. Target columns are intentionally not
    part of the streaming state contract.
    """

    rows = [dict(event) if isinstance(event, Mapping) else event.to_dict() for event in events]
    if not rows:
        raise ValueError("cannot aggregate an empty flow window")
    frame = pd.DataFrame(rows)
    if "timestamp_parsed" not in frame.columns:
        if "timestamp" not in frame.columns:
            raise ValueError("flow events require timestamp or timestamp_parsed")
        frame["timestamp_parsed"] = pd.to_datetime(frame["timestamp"], errors="coerce", format="mixed")
    if "capture_date" not in frame.columns:
        timestamps = pd.to_datetime(frame["timestamp_parsed"], errors="coerce", format="mixed")
        frame["capture_date"] = timestamps.dt.strftime("%Y-%m-%d")
    missing = sorted(REQUIRED_COLUMNS.difference(frame.columns))
    if missing:
        raise ValueError(f"flow event is missing required aggregation fields: {missing}")

    states, _ = aggregate_network_states(frame, interval_seconds=interval_seconds)
    if len(states) != 1:
        raise ValueError("one flow window must produce exactly one network state")
    state = states.iloc[[0]][STATE_COLUMNS].copy()
    return _ensure_state_columns(state)


def state_from_replay_event(event: Mapping[str, Any]) -> pd.DataFrame:
    """Validate a replay event that already contains an approved network state."""

    payload = event.get("payload", event)
    if not isinstance(payload, Mapping):
        raise TypeError("state replay event payload must be a mapping")
    return validate_state(payload)
