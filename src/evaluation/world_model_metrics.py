"""Evaluation metrics for the LSTM world-model experiment."""

from __future__ import annotations

from typing import Any, Iterable

import numpy as np
from sklearn.metrics import average_precision_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score


def evaluate_binary(y_true: np.ndarray, probabilities: np.ndarray, threshold: float = 0.5) -> dict[str, Any]:
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be in [0, 1]")
    labels = np.asarray(y_true, dtype="int8")
    scores = np.asarray(probabilities, dtype="float64")
    if labels.ndim != 1 or scores.ndim != 1 or len(labels) != len(scores) or len(labels) == 0:
        raise ValueError("y_true and probabilities must be non-empty equal-length vectors")
    if set(np.unique(labels)) - {0, 1}:
        raise ValueError("y_true must contain only 0 and 1")
    if not np.isfinite(scores).all() or ((scores < 0) | (scores > 1)).any():
        raise ValueError("probabilities must be finite values in [0, 1]")
    predictions = (scores >= threshold).astype("int8")
    matrix = confusion_matrix(labels, predictions, labels=[0, 1])
    tn, fp, fn, tp = (int(value) for value in matrix.ravel())
    both_classes = np.unique(labels).size == 2
    return {
        "threshold": float(threshold),
        "precision": float(precision_score(labels, predictions, zero_division=0)),
        "recall": float(recall_score(labels, predictions, zero_division=0)),
        "f1": float(f1_score(labels, predictions, zero_division=0)),
        "pr_auc": float(average_precision_score(labels, scores)) if both_classes else None,
        "roc_auc": float(roc_auc_score(labels, scores)) if both_classes else None,
        "false_positive_rate": float(fp / (fp + tn)) if (fp + tn) else None,
        "confusion_matrix": [[tn, fp], [fn, tp]],
        "positive_support": int((labels == 1).sum()),
        "negative_support": int((labels == 0).sum()),
    }


def threshold_table(y_true: np.ndarray, probabilities: np.ndarray, thresholds: Iterable[float]) -> list[dict[str, Any]]:
    return [evaluate_binary(y_true, probabilities, float(threshold)) for threshold in thresholds]


def select_threshold_by_validation(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("Validation threshold results are required")
    return sorted(rows, key=lambda row: (-row["f1"], row["threshold"]))[0]
