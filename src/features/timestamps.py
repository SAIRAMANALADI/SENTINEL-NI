"""Timestamp parsing for the CSE-CIC-IDS2018 flow export."""

from __future__ import annotations

import pandas as pd


SOURCE_TIMESTAMP_COLUMN = "Timestamp"
PARSED_TIMESTAMP_COLUMN = "timestamp_parsed"
TIMESTAMP_FORMAT = "%d/%m/%Y %H:%M:%S"


def parse_timestamp_column(frame: pd.DataFrame) -> pd.DataFrame:
    """Parse timestamps without assigning or converting a timezone."""
    if SOURCE_TIMESTAMP_COLUMN not in frame.columns:
        raise ValueError(f"Required timestamp column is missing: {SOURCE_TIMESTAMP_COLUMN}")

    result = frame.copy()
    result[PARSED_TIMESTAMP_COLUMN] = pd.to_datetime(
        result[SOURCE_TIMESTAMP_COLUMN],
        format=TIMESTAMP_FORMAT,
        errors="coerce",
    )
    return result


def timestamp_audit(frame: pd.DataFrame) -> dict[str, object]:
    """Return timestamp validity and ordering diagnostics."""
    if PARSED_TIMESTAMP_COLUMN not in frame.columns:
        raise ValueError(f"Parsed timestamp column is missing: {PARSED_TIMESTAMP_COLUMN}")

    parsed = frame[PARSED_TIMESTAMP_COLUMN]
    decreases = parsed.diff().dt.total_seconds().lt(0).fillna(False)
    return {
        "missing_or_invalid_count": int(parsed.isna().sum()),
        "chronologically_ordered": not bool(decreases.any()),
        "chronological_backsteps": int(decreases.sum()),
        "min": parsed.min().isoformat(sep=" ") if parsed.notna().any() else None,
        "max": parsed.max().isoformat(sep=" ") if parsed.notna().any() else None,
        "timezone_assumption": "naive local capture timestamps; no timezone conversion applied",
    }
