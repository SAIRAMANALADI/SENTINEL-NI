from __future__ import annotations

import pandas as pd
import pytest

from src.features.labels import add_label_columns, validate_labels


def test_binary_mapping_preserves_original_label() -> None:
    frame = add_label_columns(pd.DataFrame({"Label": ["Benign", "Infilteration"]}))

    assert frame["Label"].tolist() == ["Benign", "Infilteration"]
    assert frame["original_label"].tolist() == ["Benign", "Infilteration"]
    assert frame["binary_label"].tolist() == [0, 1]


def test_invalid_label_is_reported_and_rejected() -> None:
    audit = validate_labels(["Benign", "Unexpected"])
    assert audit["valid"] is False
    assert audit["invalid_values"] == ["Unexpected"]
    with pytest.raises(ValueError, match="Invalid or missing labels"):
        add_label_columns(pd.DataFrame({"Label": ["Benign", "Unexpected"]}))
