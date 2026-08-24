"""Chronological, class-aware splitting for the single CSE-CIC-IDS2018 day."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


TIMESTAMP_COLUMN = "timestamp_parsed"
TARGET_COLUMN = "binary_label"
SPLIT_COLUMN = "split"
DEFAULT_BOUNDARIES = {
    "train_start": "2018-02-28 01:00:00",
    "validation_start": "2018-02-28 02:30:00",
    "test_start": "2018-02-28 02:45:00",
    "test_end": "2018-02-28 12:59:59",
}


@dataclass(frozen=True)
class ChronologicalSplit:
    frame: pd.DataFrame
    report: dict[str, Any]


def _label_summary(values: pd.Series) -> dict[str, Any]:
    counts = values.value_counts().sort_index().to_dict()
    total = len(values)
    return {
        "counts": {str(int(key)): int(value) for key, value in counts.items()},
        "total": int(total),
        "positive_rate": float(values.mean()) if total else None,
    }


def chronological_split(
    frame: pd.DataFrame,
    boundaries: dict[str, str] | None = None,
    timestamp_column: str = TIMESTAMP_COLUMN,
    target_column: str = TARGET_COLUMN,
) -> ChronologicalSplit:
    """Sort by timestamp and assign contiguous train/validation/test blocks.

    The boundaries are intentionally data-informed: a 60/20/20 time split
    produced an all-benign validation set, so the early attack block is used
    for validation and the later attack block remains a future test period.
    """
    if timestamp_column not in frame.columns:
        raise ValueError(f"Missing timestamp column: {timestamp_column}")
    if target_column not in frame.columns:
        raise ValueError(f"Missing target column: {target_column}")

    chosen = dict(DEFAULT_BOUNDARIES)
    if boundaries:
        chosen.update(boundaries)
    parsed = {key: pd.Timestamp(value) for key, value in chosen.items()}
    if not (parsed["train_start"] < parsed["validation_start"] < parsed["test_start"] <= parsed["test_end"]):
        raise ValueError(f"Invalid chronological boundaries: {chosen}")

    result = frame.copy()
    result[timestamp_column] = pd.to_datetime(result[timestamp_column], errors="coerce")
    if result[timestamp_column].isna().any():
        raise ValueError("Cannot split rows with missing or invalid timestamps")
    source_order_was_chronological = bool(result[timestamp_column].is_monotonic_increasing)
    sort_columns = [timestamp_column]
    if "source_row_number" in result.columns:
        sort_columns.append("source_row_number")
    result = result.sort_values(sort_columns, kind="mergesort").reset_index(drop=True)

    timestamps = result[timestamp_column]
    split = pd.Series("unassigned", index=result.index, dtype="string")
    split.loc[(timestamps >= parsed["train_start"]) & (timestamps < parsed["validation_start"])] = "train"
    split.loc[(timestamps >= parsed["validation_start"]) & (timestamps < parsed["test_start"])] = "validation"
    split.loc[(timestamps >= parsed["test_start"]) & (timestamps <= parsed["test_end"])] = "test"
    if split.eq("unassigned").any():
        unassigned = int(split.eq("unassigned").sum())
        raise ValueError(f"{unassigned} rows fall outside the configured split boundaries")
    result[SPLIT_COLUMN] = split

    report: dict[str, Any] = {
        "method": "contiguous chronological split after stable timestamp sort",
        "random_split_used": False,
        "timestamp_column": timestamp_column,
        "target_column": target_column,
        "boundaries": {key: value.isoformat(sep=" ") for key, value in parsed.items()},
        "dataset_timestamp_min": timestamps.min().isoformat(sep=" "),
        "dataset_timestamp_max": timestamps.max().isoformat(sep=" "),
        "source_order_was_chronological": source_order_was_chronological,
        "split_counts": {},
        "class_distribution": {},
    }
    for name in ("train", "validation", "test"):
        part = result[result[SPLIT_COLUMN] == name]
        report["split_counts"][name] = int(len(part))
        report["class_distribution"][name] = _label_summary(part[target_column])

    return ChronologicalSplit(result, report)
