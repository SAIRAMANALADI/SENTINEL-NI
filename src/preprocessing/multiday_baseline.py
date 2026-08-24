"""Target-gated, capture-day-aware Logistic Regression baseline framework."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import yaml

DEFAULT_DAY_ROLES = {
    "2018-02-14": "train",
    "2018-02-21": "train",
    "2018-02-22": "validation",
    "2018-02-28": "test",
}
PROVENANCE_COLUMNS = {
    "source_file",
    "capture_date",
    "source_row_number",
    "Timestamp",
    "timestamp_parsed",
    "timestamp_capture_date_mismatch",
    "Label",
    "original_label",
}


def target_spec_status(target_spec_path: str | Path) -> dict[str, Any]:
    """Return availability without inferring or defaulting a target rule."""
    path = Path(target_spec_path).expanduser().resolve()
    if not path.is_file():
        return {
            "available": False,
            "path": str(path),
            "reason": "Approved multi-day target specification is missing; no target rule was inferred.",
        }
    text = path.read_text(encoding="utf-8")
    if "APPROVED" not in text.upper():
        return {
            "available": False,
            "path": str(path),
            "reason": "Target specification exists but is not explicitly marked APPROVED.",
        }
    return {"available": True, "path": str(path), "reason": "Explicitly approved specification found."}


def load_day_roles(path: str | Path) -> dict[str, str]:
    report = json.loads(Path(path).read_text(encoding="utf-8"))
    roles: dict[str, str] = {}
    for split_name in ("train", "validation", "test"):
        for capture_day in report[f"{split_name}_days"]:
            if capture_day in roles:
                raise ValueError(f"Capture day assigned to multiple splits: {capture_day}")
            roles[capture_day] = split_name
    if not roles:
        raise ValueError("No capture-day assignments found")
    return roles


def assign_day_splits(frame: pd.DataFrame, day_roles: dict[str, str]) -> pd.DataFrame:
    """Assign complete capture days without random row distribution."""
    required = {"capture_date", "timestamp_parsed", "source_row_number"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"Missing day-aware split columns: {missing}")
    result = frame.copy()
    result["split"] = result["capture_date"].astype("string").map(day_roles)
    if result["split"].isna().any():
        unknown = sorted(result.loc[result["split"].isna(), "capture_date"].astype(str).unique())
        raise ValueError(f"Capture dates have no assigned split: {unknown}")
    result = result.sort_values(
        ["capture_date", "timestamp_parsed", "source_row_number"],
        kind="mergesort",
    ).reset_index(drop=True)
    observed = result.groupby("split")["capture_date"].nunique().to_dict()
    if any(int(count) < 1 for count in observed.values()):
        raise ValueError("Every split must contain at least one complete capture day")
    return result


def load_exclusions(path: str | Path) -> set[str]:
    document = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    fields = document.get("fields", []) if isinstance(document, dict) else []
    return {str(entry["field"]) for entry in fields}


def select_multiday_features(
    frame: pd.DataFrame,
    exclusions: Iterable[str],
    target_column: str,
) -> list[str]:
    """Select finite numeric flow features while excluding target/provenance fields."""
    excluded = set(exclusions) | PROVENANCE_COLUMNS | {target_column}
    columns = [
        column
        for column in frame.columns
        if column not in excluded and pd.api.types.is_numeric_dtype(frame[column])
    ]
    if not columns:
        raise ValueError("No numeric model features remain after target/provenance exclusions")
    values = frame[columns]
    if values.isna().any().any() or not np.isfinite(values.to_numpy(dtype="float64")).all():
        raise ValueError("Selected model features contain missing or non-finite values")
    return columns


def build_explicit_binary_target(
    labels: pd.Series,
    positive_labels: Iterable[str],
) -> np.ndarray:
    """Build a target only from labels explicitly supplied by an approved spec."""
    positive = {str(label) for label in positive_labels}
    if not positive:
        raise ValueError("An approved target must provide at least one positive source label")
    unknown = sorted(set(labels.astype("string").dropna().unique()) - positive - {"Benign"})
    if unknown:
        raise ValueError(
            "Approved target does not account for source labels: "
            f"{unknown}. No implicit mapping is allowed."
        )
    return labels.astype("string").isin(positive).astype("int8").to_numpy()
