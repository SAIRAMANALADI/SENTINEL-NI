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


@dataclass(frozen=True)
class SequenceBatch:
    """Deterministic fixed-length sequences and their already-aligned targets."""

    features: np.ndarray
    targets: np.ndarray
    origins: np.ndarray
    target_times: np.ndarray
    groups: np.ndarray
    splits: np.ndarray
    input_end_positions: np.ndarray
    target_positions: np.ndarray
    report: dict[str, Any]


@dataclass(frozen=True)
class MultiStepSequenceBatch:
    """Historical state windows paired with a vector of future state labels."""

    features: np.ndarray
    targets: np.ndarray
    origins: np.ndarray
    target_times: np.ndarray
    groups: np.ndarray
    splits: np.ndarray
    input_end_positions: np.ndarray
    target_positions: np.ndarray
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


def _validate_positive_integer(name: str, value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or value < 1:
        raise ValueError(f"{name} must be a positive integer")


def _validate_fixed_state_cadence(
    working: pd.DataFrame,
    grouping_columns: list[str],
    group_column: str,
    interval_seconds: int,
) -> None:
    """Reject state rows that are not ordered at the approved fixed cadence."""

    _validate_positive_integer("interval_seconds", interval_seconds)
    if working.empty:
        return
    expected_delta = pd.Timedelta(seconds=int(interval_seconds))
    if group_column == "capture_day":
        capture_days = working[group_column].astype("string")
        timestamp_dates = working["__timestamp"].dt.strftime("%Y-%m-%d")
        if timestamp_dates.ne(capture_days).any():
            raise ValueError("timestamp dates must match capture_day for every state")

    for key, group in working.groupby(grouping_columns, sort=False, dropna=False):
        deltas = group["__timestamp"].diff().dropna()
        if (deltas <= pd.Timedelta(0)).any():
            raise ValueError(f"timestamps must be strictly increasing within group {key!r}")
        if not (deltas == expected_delta).all():
            raise ValueError(
                f"timestamps must be exactly {interval_seconds} seconds apart within group {key!r}"
            )


def build_sequences(
    dataframe: pd.DataFrame,
    feature_columns: list[str],
    target_column: str,
    sequence_length: int,
    forecast_horizon: int,
    stride: int = 1,
    group_column: str = "capture_day",
    interval_seconds: int = 10,
) -> SequenceBatch:
    """Build chronological, group-isolated sequences from state rows.

    For the frozen V1 target ``future_attack_state``, each sequence
    ``S(t-L+1), ..., S(t)`` receives the target already stored on the final
    input row: ``future_attack_state(t)``.  No additional target shift is
    applied.  The one-step horizon is therefore required for that column.

    For a non-pre-aligned target column, ``forecast_horizon=K`` selects the
    target at ``K`` rows after the final input row.  This generic path supports
    unit tests and future explicitly current-state target columns without
    changing the frozen V1 contract.

    If a ``split`` column is present, sequences are grouped by
    ``(split, group_column)``.  Otherwise they are grouped by ``group_column``.
    Stable timestamp ordering is applied inside every group; equal timestamps
    retain their input order.  Empty inputs return correctly shaped empty
    arrays rather than fabricating a sequence.
    """

    _validate_positive_integer("sequence_length", sequence_length)
    _validate_positive_integer("forecast_horizon", forecast_horizon)
    _validate_positive_integer("stride", stride)
    _validate_positive_integer("interval_seconds", interval_seconds)
    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe must be a pandas DataFrame")
    if not feature_columns:
        raise ValueError("feature_columns must not be empty")
    if len(set(feature_columns)) != len(feature_columns):
        raise ValueError("feature_columns must be unique")
    required = set(feature_columns) | {target_column, "timestamp", group_column}
    missing = sorted(required - set(dataframe.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    if not pd.api.types.is_numeric_dtype(dataframe[target_column]):
        raise TypeError("target column must be numeric")
    if target_column == "future_attack_state" and forecast_horizon != 1:
        raise ValueError("future_attack_state is already one-step aligned; forecast_horizon must be 1")

    feature_count = len(feature_columns)
    if dataframe.empty:
        empty_target = np.empty((0,), dtype=dataframe[target_column].dtype)
        empty_time = np.empty((0,), dtype="datetime64[ns]")
        empty_text = np.empty((0,), dtype="U1")
        return SequenceBatch(
            np.empty((0, sequence_length, feature_count), dtype="float32"),
            empty_target,
            empty_time,
            empty_time.copy(),
            empty_text,
            empty_text.copy(),
            np.empty((0,), dtype="int64"),
            np.empty((0,), dtype="int64"),
            {
                "sequence_length": int(sequence_length),
                "forecast_horizon": int(forecast_horizon),
                "stride": int(stride),
                "interval_seconds": int(interval_seconds),
                "feature_dimension": feature_count,
                "sequence_count": 0,
                "target_alignment": "pre-aligned final input row" if target_column == "future_attack_state" else "future row offset",
            },
        )

    working = dataframe.reset_index(drop=True).copy()
    working["__input_position"] = np.arange(len(working), dtype="int64")
    working["__timestamp"] = pd.to_datetime(working["timestamp"], errors="coerce")
    if working["__timestamp"].isna().any():
        raise ValueError("timestamp contains invalid values")
    if working[group_column].isna().any():
        raise ValueError(f"{group_column} contains missing values")
    feature_matrix = working[feature_columns].to_numpy(dtype="float32")
    if not np.isfinite(feature_matrix).all():
        raise ValueError("model features contain NaN or Inf")
    target_values = working[target_column].to_numpy()
    if not np.isfinite(target_values.astype("float64")).all():
        raise ValueError("target column contains NaN or Inf")

    working["__group_value"] = working[group_column].astype("string")
    grouping_columns = ["__group_value"]
    has_split = "split" in working.columns
    if has_split:
        working["__split_value"] = working["split"].astype("string")
        if working["__split_value"].isna().any():
            raise ValueError("split contains missing values")
        grouping_columns.insert(0, "__split_value")
    _validate_fixed_state_cadence(working, grouping_columns, group_column, interval_seconds)
    working = working.sort_values(
        grouping_columns + ["__timestamp", "__input_position"],
        kind="mergesort",
    ).reset_index(drop=True)
    sorted_features = working[feature_columns].to_numpy(dtype="float32")
    sorted_targets = working[target_column].to_numpy()
    sorted_times = working["__timestamp"].to_numpy(dtype="datetime64[ns]")
    sorted_input_positions = working["__input_position"].to_numpy(dtype="int64")
    pre_aligned = target_column == "future_attack_state"
    availability = (
        working["future_target_available"].astype(bool).to_numpy()
        if "future_target_available" in working.columns
        else np.ones(len(working), dtype=bool)
    )

    sequence_features: list[np.ndarray] = []
    sequence_targets: list[object] = []
    sequence_origins: list[np.datetime64] = []
    sequence_target_times: list[np.datetime64] = []
    sequence_groups: list[str] = []
    sequence_splits: list[str] = []
    sequence_input_ends: list[int] = []
    sequence_target_positions: list[int] = []
    group_counts: dict[str, int] = {}

    grouped = working.groupby(grouping_columns, sort=False, dropna=False).indices
    for key, group_positions in grouped.items():
        positions = np.asarray(group_positions, dtype="int64")
        group_size = len(positions)
        target_offset = 0 if pre_aligned else forecast_horizon
        available = group_size - sequence_length - target_offset + 1
        key_values = key if isinstance(key, tuple) else (key,)
        split_value = str(key_values[0]) if has_split else ""
        group_value = str(key_values[-1])
        created = 0
        if available > 0:
            for start in range(0, available, stride):
                end = start + sequence_length - 1
                target_index = end + target_offset
                target_position = int(positions[target_index])
                if not availability[target_position]:
                    continue
                sequence_features.append(sorted_features[positions[start : end + 1]])
                sequence_targets.append(sorted_targets[target_position])
                sequence_origins.append(sorted_times[positions[end]])
                sequence_target_times.append(sorted_times[target_position])
                sequence_groups.append(group_value)
                sequence_splits.append(split_value)
                sequence_input_ends.append(int(sorted_input_positions[positions[end]]))
                sequence_target_positions.append(int(sorted_input_positions[target_position]))
                created += 1
        group_counts[f"{split_value}/{group_value}" if has_split else group_value] = created

    if sequence_features:
        output_features = np.stack(sequence_features).astype("float32")
        output_targets = np.asarray(sequence_targets, dtype=dataframe[target_column].dtype)
    else:
        output_features = np.empty((0, sequence_length, feature_count), dtype="float32")
        output_targets = np.empty((0,), dtype=dataframe[target_column].dtype)
    output_origins = np.asarray(sequence_origins, dtype="datetime64[ns]")
    output_target_times = np.asarray(sequence_target_times, dtype="datetime64[ns]")
    output_groups = np.asarray(sequence_groups, dtype="U")
    output_splits = np.asarray(sequence_splits, dtype="U")
    output_input_ends = np.asarray(sequence_input_ends, dtype="int64")
    output_target_positions = np.asarray(sequence_target_positions, dtype="int64")
    report = {
        "sequence_length": int(sequence_length),
        "forecast_horizon": int(forecast_horizon),
        "stride": int(stride),
        "interval_seconds": int(interval_seconds),
        "feature_dimension": feature_count,
        "sequence_count": int(len(output_targets)),
        "group_column": group_column,
        "split_column_used": has_split,
        "group_counts": group_counts,
        "target_alignment": (
            "future_attack_state is read from the final input row; no second shift"
            if pre_aligned
            else "target is read forecast_horizon rows after the final input row"
        ),
        "cross_group_sequences": False,
        "deterministic_sort": "stable timestamp order with original-row tie break",
    }
    return SequenceBatch(
        output_features,
        output_targets,
        output_origins,
        output_target_times,
        output_groups,
        output_splits,
        output_input_ends,
        output_target_positions,
        report,
    )


def build_multistep_sequences(
    dataframe: pd.DataFrame,
    feature_columns: list[str],
    target_source_column: str,
    sequence_length: int,
    forecast_horizon: int,
    stride: int = 1,
    group_column: str = "capture_day",
    interval_seconds: int = 10,
) -> MultiStepSequenceBatch:
    """Build direct multi-step targets without shifting the approved target twice.

    The frozen state table stores ``binary_attack_state`` at each state time and
    stores ``future_attack_state(t)`` as the already-aligned label for the next
    state. For an input ending at state ``t``, this function reads the source
    column from the next ``forecast_horizon`` rows in the same group:

    ``X = S(t-L+1)..S(t)``
    ``Y = [binary_attack_state(t+10), ..., binary_attack_state(t+K*10)]``

    Therefore K=1 is equivalent to the existing ``future_attack_state(t)``
    target, while K=3 and K=5 read the later current-state labels directly.
    No second shift is applied to ``future_attack_state``. The returned shapes
    are ``features=(N, sequence_length, feature_count)`` and
    ``targets=(N, forecast_horizon)``; target timestamps and original row
    positions have shape ``(N, forecast_horizon)``.

    Groups are ``(split, group_column)`` when a split column is present, and
    ``group_column`` otherwise. Stable timestamp ordering and original-row
    tie-breaking make output deterministic. A window is emitted only when all
    required future rows exist in the same group.
    """

    _validate_positive_integer("sequence_length", sequence_length)
    _validate_positive_integer("forecast_horizon", forecast_horizon)
    _validate_positive_integer("stride", stride)
    _validate_positive_integer("interval_seconds", interval_seconds)
    if not isinstance(dataframe, pd.DataFrame):
        raise TypeError("dataframe must be a pandas DataFrame")
    if not feature_columns:
        raise ValueError("feature_columns must not be empty")
    if len(set(feature_columns)) != len(feature_columns):
        raise ValueError("feature_columns must be unique")
    if target_source_column == "future_attack_state":
        raise ValueError(
            "Use binary_attack_state as the multi-step source; "
            "future_attack_state is already +10s aligned"
        )
    required = set(feature_columns) | {target_source_column, "timestamp", group_column}
    missing = sorted(required - set(dataframe.columns))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    if not pd.api.types.is_numeric_dtype(dataframe[target_source_column]):
        raise TypeError("target source column must be numeric")

    feature_count = len(feature_columns)
    if dataframe.empty:
        return MultiStepSequenceBatch(
            np.empty((0, sequence_length, feature_count), dtype="float32"),
            np.empty((0, forecast_horizon), dtype="int8"),
            np.empty((0,), dtype="datetime64[ns]"),
            np.empty((0, forecast_horizon), dtype="datetime64[ns]"),
            np.empty((0,), dtype="U1"),
            np.empty((0,), dtype="U1"),
            np.empty((0,), dtype="int64"),
            np.empty((0, forecast_horizon), dtype="int64"),
            {
                "sequence_length": int(sequence_length),
                "forecast_horizon": int(forecast_horizon),
                "stride": int(stride),
                "interval_seconds": int(interval_seconds),
                "feature_dimension": feature_count,
                "target_dimension": int(forecast_horizon),
                "sequence_count": 0,
                "target_source_column": target_source_column,
                "target_alignment": "direct future rows; no second shift",
            },
        )

    working = dataframe.reset_index(drop=True).copy()
    working["__input_position"] = np.arange(len(working), dtype="int64")
    working["__timestamp"] = pd.to_datetime(working["timestamp"], errors="coerce")
    if working["__timestamp"].isna().any():
        raise ValueError("timestamp contains invalid values")
    if working[group_column].isna().any():
        raise ValueError(f"{group_column} contains missing values")

    feature_matrix = working[feature_columns].to_numpy(dtype="float32")
    if not np.isfinite(feature_matrix).all():
        raise ValueError("model features contain NaN or Inf")
    source_values = working[target_source_column].to_numpy()
    if not np.isfinite(source_values.astype("float64")).all():
        raise ValueError("target source column contains NaN or Inf")
    if set(np.unique(source_values)) - {0, 1}:
        raise ValueError("target source column must contain only 0 and 1")

    working["__group_value"] = working[group_column].astype("string")
    grouping_columns = ["__group_value"]
    has_split = "split" in working.columns
    if has_split:
        working["__split_value"] = working["split"].astype("string")
        if working["__split_value"].isna().any():
            raise ValueError("split contains missing values")
        grouping_columns.insert(0, "__split_value")
    _validate_fixed_state_cadence(working, grouping_columns, group_column, interval_seconds)
    working = working.sort_values(
        grouping_columns + ["__timestamp", "__input_position"],
        kind="mergesort",
    ).reset_index(drop=True)

    sorted_features = working[feature_columns].to_numpy(dtype="float32")
    sorted_sources = working[target_source_column].to_numpy()
    sorted_times = working["__timestamp"].to_numpy(dtype="datetime64[ns]")
    sorted_input_positions = working["__input_position"].to_numpy(dtype="int64")

    sequence_features: list[np.ndarray] = []
    sequence_targets: list[np.ndarray] = []
    sequence_origins: list[np.datetime64] = []
    sequence_target_times: list[np.ndarray] = []
    sequence_groups: list[str] = []
    sequence_splits: list[str] = []
    sequence_input_ends: list[int] = []
    sequence_target_positions: list[np.ndarray] = []
    group_counts: dict[str, int] = {}

    grouped = working.groupby(grouping_columns, sort=False, dropna=False).indices
    for key, group_positions in grouped.items():
        positions = np.asarray(group_positions, dtype="int64")
        available = len(positions) - sequence_length - forecast_horizon + 1
        key_values = key if isinstance(key, tuple) else (key,)
        split_value = str(key_values[0]) if has_split else ""
        group_value = str(key_values[-1])
        created = 0
        if available > 0:
            for start in range(0, available, stride):
                input_end = start + sequence_length - 1
                future_positions = positions[input_end + 1 : input_end + 1 + forecast_horizon]
                if len(future_positions) != forecast_horizon:
                    continue
                input_positions = positions[start : input_end + 1]
                future_times = sorted_times[future_positions]
                if not (future_times > sorted_times[positions[input_end]]).all():
                    raise ValueError("future target timestamps must be after the input origin")
                sequence_features.append(sorted_features[input_positions])
                sequence_targets.append(sorted_sources[future_positions].astype("int8"))
                sequence_origins.append(sorted_times[positions[input_end]])
                sequence_target_times.append(future_times)
                sequence_groups.append(group_value)
                sequence_splits.append(split_value)
                sequence_input_ends.append(int(sorted_input_positions[positions[input_end]]))
                sequence_target_positions.append(sorted_input_positions[future_positions])
                created += 1
        group_counts[f"{split_value}/{group_value}" if has_split else group_value] = created

    if sequence_features:
        output_features = np.stack(sequence_features).astype("float32")
        output_targets = np.stack(sequence_targets).astype("int8")
        output_target_times = np.stack(sequence_target_times).astype("datetime64[ns]")
        output_target_positions = np.stack(sequence_target_positions).astype("int64")
    else:
        output_features = np.empty((0, sequence_length, feature_count), dtype="float32")
        output_targets = np.empty((0, forecast_horizon), dtype="int8")
        output_target_times = np.empty((0, forecast_horizon), dtype="datetime64[ns]")
        output_target_positions = np.empty((0, forecast_horizon), dtype="int64")
    output_origins = np.asarray(sequence_origins, dtype="datetime64[ns]")
    output_groups = np.asarray(sequence_groups, dtype="U")
    output_splits = np.asarray(sequence_splits, dtype="U")
    output_input_ends = np.asarray(sequence_input_ends, dtype="int64")
    report = {
        "sequence_length": int(sequence_length),
        "forecast_horizon": int(forecast_horizon),
        "stride": int(stride),
        "interval_seconds": int(interval_seconds),
        "feature_dimension": feature_count,
        "target_dimension": int(forecast_horizon),
        "sequence_count": int(len(output_targets)),
        "group_column": group_column,
        "split_column_used": has_split,
        "group_counts": group_counts,
        "target_source_column": target_source_column,
        "target_alignment": "direct future rows at +10s increments; no second shift",
        "cross_group_sequences": False,
        "deterministic_sort": "stable timestamp order with original-row tie break",
    }
    return MultiStepSequenceBatch(
        output_features,
        output_targets,
        output_origins,
        output_target_times,
        output_groups,
        output_splits,
        output_input_ends,
        output_target_positions,
        report,
    )
