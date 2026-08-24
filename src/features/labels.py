"""Label validation and derived binary-label handling for CSE-CIC-IDS2018."""

from __future__ import annotations

from typing import Iterable

import pandas as pd


LABEL_COLUMN = "Label"
ORIGINAL_LABEL_COLUMN = "original_label"
BINARY_LABEL_COLUMN = "binary_label"
LABEL_MAPPING = {"Benign": 0, "Infilteration": 1}


def validate_labels(labels: Iterable[str]) -> dict[str, object]:
    """Return a structured label audit without changing the source values."""
    series = pd.Series(labels, dtype="string")
    counts = series.value_counts(dropna=False).to_dict()
    invalid = sorted(
        str(value)
        for value in series.dropna().unique()
        if str(value) not in LABEL_MAPPING
    )
    missing = int(series.isna().sum())
    return {
        "counts": {str(key): int(value) for key, value in counts.items()},
        "invalid_values": invalid,
        "missing_count": missing,
        "valid": not invalid and missing == 0,
    }


def add_label_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Add target views while retaining the original ``Label`` column exactly."""
    if LABEL_COLUMN not in frame.columns:
        raise ValueError(f"Required label column is missing: {LABEL_COLUMN}")

    audit = validate_labels(frame[LABEL_COLUMN])
    if not audit["valid"]:
        raise ValueError(
            "Invalid or missing labels: "
            f"invalid={audit['invalid_values']}, missing={audit['missing_count']}"
        )

    result = frame.copy()
    result[ORIGINAL_LABEL_COLUMN] = result[LABEL_COLUMN].astype("string")
    result[BINARY_LABEL_COLUMN] = result[ORIGINAL_LABEL_COLUMN].map(LABEL_MAPPING).astype("int8")
    return result
