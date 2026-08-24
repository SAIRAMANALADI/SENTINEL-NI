"""Deterministic, split-isolated temporal row windows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class TemporalWindowResult:
    features: dict[str, np.ndarray]
    targets: dict[str, np.ndarray]
    origins: dict[str, np.ndarray]
    target_times: dict[str, np.ndarray]
    origin_positions: dict[str, np.ndarray]
    target_positions: dict[str, np.ndarray]
    report: dict[str, Any]


def generate_temporal_windows(
    features: pd.DataFrame,
    timestamps: pd.Series,
    targets: pd.Series,
    splits: pd.Series,
    sequence_length: int,
    stride: int = 1,
    forecast_horizon: int = 1,
) -> TemporalWindowResult:
    """Create ``S(t-L+1)..S(t) -> y(t+K)`` windows within each split only."""
    if sequence_length < 1 or stride < 1 or forecast_horizon < 1:
        raise ValueError("sequence_length, stride, and forecast_horizon must be positive")
    if not (len(features) == len(timestamps) == len(targets) == len(splits)):
        raise ValueError("features, timestamps, targets, and splits must have equal lengths")
    if features.empty:
        raise ValueError("Cannot generate windows from an empty feature table")
    if not all(pd.api.types.is_numeric_dtype(features[column]) for column in features.columns):
        raise TypeError("Temporal windows require numeric features")

    matrix = features.to_numpy(dtype="float32")
    if not np.isfinite(matrix).all():
        raise ValueError("Temporal windows received non-finite features")
    times = pd.to_datetime(timestamps, errors="coerce")
    if times.isna().any():
        raise ValueError("Temporal windows received invalid timestamps")
    split_values = splits.astype("string")
    output_features: dict[str, np.ndarray] = {}
    output_targets: dict[str, np.ndarray] = {}
    output_origins: dict[str, np.ndarray] = {}
    output_target_times: dict[str, np.ndarray] = {}
    output_origin_positions: dict[str, np.ndarray] = {}
    output_target_positions: dict[str, np.ndarray] = {}
    counts: dict[str, int] = {}
    timestamp_alignment: dict[str, dict[str, int | bool]] = {}

    for split_name in ("train", "validation", "test"):
        positions = np.flatnonzero(split_values.to_numpy() == split_name)
        available = len(positions) - sequence_length - forecast_horizon + 1
        if available <= 0:
            shape = (0, sequence_length, matrix.shape[1])
            output_features[split_name] = np.empty(shape, dtype="float32")
            output_targets[split_name] = np.empty((0,), dtype="int8")
            output_origins[split_name] = np.empty((0,), dtype="datetime64[ns]")
            output_target_times[split_name] = np.empty((0,), dtype="datetime64[ns]")
            output_origin_positions[split_name] = np.empty((0,), dtype="int64")
            output_target_positions[split_name] = np.empty((0,), dtype="int64")
            counts[split_name] = 0
            timestamp_alignment[split_name] = {
                "strict_future_timestamp_count": 0,
                "same_timestamp_target_count": 0,
                "target_row_after_origin": True,
            }
            continue

        starts = range(0, available, stride)
        window_features = []
        window_targets = []
        window_origins = []
        window_target_times = []
        window_origin_positions = []
        window_target_positions = []
        for start in starts:
            input_positions = positions[start : start + sequence_length]
            target_position = positions[start + sequence_length + forecast_horizon - 1]
            window_features.append(matrix[input_positions])
            window_targets.append(int(targets.iloc[target_position]))
            window_origins.append(times.iloc[input_positions[-1]])
            window_target_times.append(times.iloc[target_position])
            window_origin_positions.append(int(input_positions[-1]))
            window_target_positions.append(int(target_position))
        output_features[split_name] = np.stack(window_features).astype("float32")
        output_targets[split_name] = np.asarray(window_targets, dtype="int8")
        output_origins[split_name] = np.asarray(window_origins, dtype="datetime64[ns]")
        output_target_times[split_name] = np.asarray(window_target_times, dtype="datetime64[ns]")
        output_origin_positions[split_name] = np.asarray(window_origin_positions, dtype="int64")
        output_target_positions[split_name] = np.asarray(window_target_positions, dtype="int64")
        counts[split_name] = len(window_targets)
        origin_times = output_origins[split_name]
        target_times = output_target_times[split_name]
        timestamp_alignment[split_name] = {
            "strict_future_timestamp_count": int((target_times > origin_times).sum()),
            "same_timestamp_target_count": int((target_times == origin_times).sum()),
            "target_row_after_origin": bool(
                (output_target_positions[split_name] > output_origin_positions[split_name]).all()
            ),
        }

    report = {
        "sequence_length": int(sequence_length),
        "stride": int(stride),
        "forecast_horizon": int(forecast_horizon),
        "feature_dimension": int(matrix.shape[1]),
        "split_window_counts": counts,
        "timestamp_alignment": timestamp_alignment,
        "target_definition": "binary attack state at t+horizon; Benign=0, Infilteration=1",
        "split_isolation": True,
        "source_order_required": "input rows must already be stably sorted by timestamp within each split",
        "causality_proof": "target row position is strictly after the final input row; timestamps are non-decreasing and may be equal for same-time flow records",
    }
    return TemporalWindowResult(
        output_features,
        output_targets,
        output_origins,
        output_target_times,
        output_origin_positions,
        output_target_positions,
        report,
    )
