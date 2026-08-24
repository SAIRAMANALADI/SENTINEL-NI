"""Score-distribution, threshold, and calibration diagnostics."""

from __future__ import annotations

from typing import Iterable

import numpy as np
from sklearn.metrics import brier_score_loss

from src.evaluation.world_model_metrics import evaluate_binary


def _validate(labels: np.ndarray, scores: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    y = np.asarray(labels, dtype="int8")
    p = np.asarray(scores, dtype="float64")
    if y.ndim != 1 or p.ndim != 1 or len(y) != len(p) or not len(y):
        raise ValueError("labels and scores must be non-empty equal-length vectors")
    if set(np.unique(y)) - {0, 1}:
        raise ValueError("labels must contain only 0 and 1")
    if not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError("scores must be finite values in [0, 1]")
    return y, p


def score_summary(labels: np.ndarray, scores: np.ndarray) -> dict[str, object]:
    y, p = _validate(labels, scores)
    quantiles = {str(q): float(np.quantile(p, q)) for q in (0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0)}
    histogram_edges = np.linspace(0.0, 1.0, 11)
    counts, _ = np.histogram(p, bins=histogram_edges)

    def class_summary(value: int) -> dict[str, object]:
        selected = p[y == value]
        return {
            "count": int(len(selected)),
            "mean": float(np.mean(selected)) if len(selected) else None,
            "std": float(np.std(selected)) if len(selected) else None,
            "quantiles": {str(q): float(np.quantile(selected, q)) for q in (0.1, 0.5, 0.9)} if len(selected) else {},
        }

    return {
        "count": int(len(y)),
        "positive_count": int((y == 1).sum()),
        "negative_count": int((y == 0).sum()),
        "overall_mean": float(np.mean(p)),
        "overall_std": float(np.std(p)),
        "quantiles": quantiles,
        "histogram_edges": histogram_edges.tolist(),
        "histogram_counts": counts.astype(int).tolist(),
        "negative_scores": class_summary(0),
        "positive_scores": class_summary(1),
    }


def calibration_bins(
    labels: np.ndarray,
    scores: np.ndarray,
    bin_edges: Iterable[float] | None = None,
) -> dict[str, object]:
    y, p = _validate(labels, scores)
    edges = np.asarray(list(bin_edges) if bin_edges is not None else np.linspace(0.0, 1.0, 11), dtype="float64")
    if len(edges) < 2 or edges[0] != 0 or edges[-1] != 1 or not np.all(np.diff(edges) > 0):
        raise ValueError("bin_edges must be increasing and span [0, 1]")
    rows = []
    absolute_gaps = []
    for index in range(len(edges) - 1):
        lower, upper = edges[index], edges[index + 1]
        mask = (p >= lower) & ((p < upper) if index < len(edges) - 2 else (p <= upper))
        count = int(mask.sum())
        mean_score = float(np.mean(p[mask])) if count else None
        observed_rate = float(np.mean(y[mask])) if count else None
        gap = abs(mean_score - observed_rate) if count else None
        if gap is not None:
            absolute_gaps.append(gap * count)
        rows.append(
            {
                "lower": float(lower),
                "upper": float(upper),
                "count": count,
                "mean_score": mean_score,
                "observed_positive_rate": observed_rate,
                "absolute_gap": gap,
            }
        )
    return {
        "bins": rows,
        "brier_score": float(brier_score_loss(y, p)),
        "expected_calibration_error": float(sum(absolute_gaps) / len(y)),
        "interpretation": "raw model scores before any post-hoc calibration",
    }


def threshold_diagnostics(
    labels: np.ndarray,
    scores: np.ndarray,
    thresholds: Iterable[float],
) -> list[dict[str, object]]:
    y, p = _validate(labels, scores)
    return [evaluate_binary(y, p, float(threshold)) for threshold in thresholds]


def compare_split_scores(
    validation_labels: np.ndarray,
    validation_scores: np.ndarray,
    test_labels: np.ndarray,
    test_scores: np.ndarray,
) -> dict[str, object]:
    """Compare frozen validation/test score distributions descriptively."""

    return {
        "validation": score_summary(validation_labels, validation_scores),
        "test": score_summary(test_labels, test_scores),
        "validation_calibration": calibration_bins(validation_labels, validation_scores),
        "test_calibration": calibration_bins(test_labels, test_scores),
    }
