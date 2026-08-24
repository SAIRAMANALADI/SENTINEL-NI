from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.preprocessing.multiday_baseline import (
    assign_day_splits,
    build_explicit_binary_target,
    select_multiday_features,
    target_spec_status,
)


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "capture_date": ["2018-02-22", "2018-02-14", "2018-02-28", "2018-02-21"],
            "timestamp_parsed": pd.to_datetime(
                ["2018-02-22 10:00", "2018-02-14 10:00", "2018-02-28 10:00", "2018-02-21 10:00"]
            ),
            "source_row_number": [1, 1, 1, 1],
            "Label": ["Web", "FTP", "Infilteration", "DDoS"],
            "original_label": ["Web", "FTP", "Infilteration", "DDoS"],
            "source_file": ["22", "14", "28", "21"],
            "source_feature": [1.0, 2.0, 3.0, 4.0],
        }
    )


def test_day_split_keeps_complete_days_and_is_deterministic() -> None:
    roles = {"2018-02-14": "train", "2018-02-21": "train", "2018-02-22": "validation", "2018-02-28": "test"}
    first = assign_day_splits(_frame(), roles)
    second = assign_day_splits(_frame(), roles)
    assert first["split"].tolist() == ["train", "train", "validation", "test"]
    assert first[["capture_date", "split"]].equals(second[["capture_date", "split"]])
    assert first.groupby("split")["capture_date"].nunique().to_dict() == {"test": 1, "train": 2, "validation": 1}


def test_feature_selection_excludes_targets_and_provenance() -> None:
    columns = select_multiday_features(_frame(), exclusions=[], target_column="binary_target")
    assert columns == ["source_feature"]


def test_target_builder_requires_explicit_label_coverage() -> None:
    labels = pd.Series(["Benign", "Infilteration", "Web"])
    target = build_explicit_binary_target(labels.iloc[:2], ["Infilteration"])
    assert np.array_equal(target, np.array([0, 1], dtype="int8"))
    try:
        build_explicit_binary_target(labels, ["Infilteration"])
    except ValueError as exc:
        assert "does not account" in str(exc)
    else:
        raise AssertionError("Unaccounted source labels must be rejected")


def test_missing_target_spec_is_blocked(tmp_path: Path) -> None:
    status = target_spec_status(tmp_path / "TARGET_STATE_SPEC.md")
    assert status["available"] is False
