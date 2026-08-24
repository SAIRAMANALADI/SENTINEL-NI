"""Leakage-neutral binary classification metrics."""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def evaluate_binary(
    y_true: np.ndarray,
    y_probability: np.ndarray,
    threshold: float = 0.5,
) -> dict[str, Any]:
    """Calculate thresholded and ranking metrics with explicit support counts."""
    y_true = np.asarray(y_true, dtype="int8")
    y_probability = np.asarray(y_probability, dtype="float64")
    if len(y_true) != len(y_probability):
        raise ValueError("y_true and y_probability lengths differ")
    if not np.isfinite(y_probability).all():
        raise ValueError("Probabilities contain non-finite values")
    y_pred = (y_probability >= threshold).astype("int8")
    matrix = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = matrix.ravel()
    both_classes = np.unique(y_true).size == 2
    report = classification_report(
        y_true,
        y_pred,
        labels=[0, 1],
        target_names=["Benign (0)", "Infilteration (1)"],
        output_dict=True,
        zero_division=0,
    )
    return {
        "threshold": float(threshold),
        "support": {"total": int(len(y_true)), "negative": int((y_true == 0).sum()), "positive": int((y_true == 1).sum())},
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "false_positive_rate": float(fp / (fp + tn)) if (fp + tn) else None,
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "roc_auc": float(roc_auc_score(y_true, y_probability)) if both_classes else None,
        "pr_auc": float(average_precision_score(y_true, y_probability)) if both_classes else None,
        "confusion_matrix": [[int(value) for value in row] for row in matrix.tolist()],
        "class_wise": report,
    }
