"""Structured validation for the cleaned CSE-CIC-IDS2018 flow table."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from src.features.labels import LABEL_MAPPING, LABEL_COLUMN, validate_labels
from src.features.timestamps import PARSED_TIMESTAMP_COLUMN, timestamp_audit


PACKET_COUNT_COLUMNS = (
    "Tot Fwd Pkts",
    "Tot Bwd Pkts",
    "Subflow Fwd Pkts",
    "Subflow Bwd Pkts",
    "Fwd Act Data Pkts",
)
BYTE_COUNT_COLUMNS = (
    "TotLen Fwd Pkts",
    "TotLen Bwd Pkts",
    "Subflow Fwd Byts",
    "Subflow Bwd Byts",
)


def _count_nonfinite(frame: pd.DataFrame) -> dict[str, int]:
    counts: dict[str, int] = {}
    for column in frame.select_dtypes(include=[np.number]).columns:
        values = frame[column].to_numpy(dtype="float64", na_value=np.nan)
        count = int(np.isinf(values).sum())
        if count:
            counts[column] = count
    return counts


def _negative_counts(frame: pd.DataFrame, columns: tuple[str, ...]) -> dict[str, int]:
    return {
        column: int(pd.to_numeric(frame[column], errors="coerce").lt(0).sum())
        for column in columns
        if column in frame.columns
    }


def validate_flow_dataframe(
    frame: pd.DataFrame,
    raw_stats: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return validation diagnostics without mutating ``frame``."""
    raw_stats = raw_stats or {}
    label_audit = validate_labels(frame[LABEL_COLUMN]) if LABEL_COLUMN in frame else {
        "counts": {},
        "invalid_values": ["missing Label column"],
        "missing_count": len(frame),
        "valid": False,
    }
    timestamp = timestamp_audit(frame) if PARSED_TIMESTAMP_COLUMN in frame else {
        "missing_or_invalid_count": len(frame),
        "chronologically_ordered": False,
        "chronological_backsteps": None,
        "min": None,
        "max": None,
        "timezone_assumption": "not available",
    }

    original_columns = list(raw_stats.get("header", []))
    if not original_columns:
        original_columns = [column for column in frame.columns if not column.endswith("__raw")]
    duplicate_view = frame[[c for c in original_columns if c in frame.columns]].copy()
    duplicate_rows = int(duplicate_view.duplicated().sum())
    duplicate_headers = int(
        frame[LABEL_COLUMN].astype("string").eq(LABEL_COLUMN).sum()
        if LABEL_COLUMN in frame
        else 0
    )

    nan_counts = {
        column: int(count)
        for column, count in frame.isna().sum().items()
        if int(count) > 0
    }
    negative_durations = int(
        pd.to_numeric(frame["Flow Duration"], errors="coerce").lt(0).sum()
        if "Flow Duration" in frame
        else 0
    )

    return {
        "row_count": len(frame),
        "column_count": len(frame.columns),
        "original_column_count": len(original_columns),
        "timestamp": timestamp,
        "chronological_ordering": {
            "ordered": timestamp["chronologically_ordered"],
            "backsteps": timestamp["chronological_backsteps"],
        },
        "duplicate_rows": duplicate_rows,
        "duplicate_header_rows": duplicate_headers,
        "labels": label_audit,
        "nan_counts": nan_counts,
        "nan_total": int(sum(nan_counts.values())),
        "infinity_counts": _count_nonfinite(frame),
        "infinity_total": int(sum(_count_nonfinite(frame).values())),
        "negative_duration_count": negative_durations,
        "negative_packet_counts": _negative_counts(frame, PACKET_COUNT_COLUMNS),
        "negative_byte_counts": _negative_counts(frame, BYTE_COUNT_COLUMNS),
        "invalid_numeric_values": raw_stats.get("numeric_parse_errors", {}),
        "ingestion": raw_stats,
        "valid_labels": sorted(LABEL_MAPPING),
    }
