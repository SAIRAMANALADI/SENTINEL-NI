from __future__ import annotations

import numpy as np

from src.evaluation.baseline_metrics import evaluate_binary, select_threshold_by_validation, threshold_table


def test_binary_metrics_include_required_outputs() -> None:
    y_true = np.asarray([0, 0, 1, 1], dtype="int8")
    probabilities = np.asarray([0.1, 0.4, 0.6, 0.9], dtype="float64")
    metrics = evaluate_binary(y_true, probabilities, threshold=0.5)

    assert metrics["confusion_matrix"] == [[2, 0], [0, 2]]
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1"] == 1.0
    assert metrics["false_positive_rate"] == 0.0
    assert metrics["pr_auc"] is not None
    assert metrics["roc_auc"] is not None
    assert metrics["positive_class_support"] == 2
    assert metrics["negative_class_support"] == 2


def test_threshold_selection_uses_validation_rows_and_is_deterministic() -> None:
    y_true = np.asarray([0, 0, 1, 1], dtype="int8")
    probabilities = np.asarray([0.2, 0.45, 0.55, 0.8], dtype="float64")
    rows = threshold_table(y_true, probabilities, [0.3, 0.5, 0.7])
    selected = select_threshold_by_validation(rows)

    assert [row["threshold"] for row in rows] == [0.3, 0.5, 0.7]
    assert selected["threshold"] in {0.3, 0.5, 0.7}


def test_metrics_reject_invalid_probabilities() -> None:
    try:
        evaluate_binary(np.asarray([0, 1], dtype="int8"), np.asarray([0.2, np.inf]))
    except ValueError as exc:
        assert "probabilities" in str(exc)
    else:
        raise AssertionError("Expected invalid probability failure")
