"""Validation-only operating-policy helpers for frozen model scores."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import numpy as np
import yaml

from src.evaluation.world_model_metrics import evaluate_binary


def validate_threshold(threshold: float) -> float:
    value = float(threshold)
    if not np.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError("threshold must be finite and in [0, 1]")
    return value


def classify_score(score: float, threshold: float) -> str:
    """Return the policy state using an inclusive warning boundary."""

    score_value = float(score)
    threshold_value = validate_threshold(threshold)
    if not np.isfinite(score_value) or not 0.0 <= score_value <= 1.0:
        raise ValueError("score must be finite and in [0, 1]")
    return "warning" if score_value >= threshold_value else "no_warning"


def _rate(numerator: int, denominator: int) -> float:
    return float(numerator / denominator) if denominator else 0.0


def compute_threshold_sweep(
    labels: np.ndarray,
    scores: np.ndarray,
    thresholds: Iterable[float],
    interval_seconds: int = 10,
) -> list[dict[str, Any]]:
    """Compute validation operating metrics for a fixed score vector.

    ``alerts_per_minute`` is a state-rate estimate: each state represents a
    fixed interval, so it is not a claim about a continuous event stream.
    """

    if isinstance(interval_seconds, bool) or interval_seconds < 1:
        raise ValueError("interval_seconds must be a positive integer")
    labels_array = np.asarray(labels)
    scores_array = np.asarray(scores)
    if labels_array.ndim != 1 or scores_array.ndim != 1 or len(labels_array) != len(scores_array):
        raise ValueError("labels and scores must be equal-length vectors")
    if len(labels_array) == 0:
        raise ValueError("labels and scores must not be empty")
    rows: list[dict[str, Any]] = []
    state_count = len(labels_array)
    for threshold in thresholds:
        value = validate_threshold(float(threshold))
        metrics = evaluate_binary(labels_array, scores_array, value)
        tn, fp = metrics["confusion_matrix"][0]
        fn, tp = metrics["confusion_matrix"][1]
        alert_count = int(fp + tp)
        rows.append(
            {
                "threshold": value,
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "f1": metrics["f1"],
                "false_positive_rate": metrics["false_positive_rate"],
                "alert_count": alert_count,
                "positive_prediction_rate": _rate(alert_count, state_count),
                "negative_prediction_rate": _rate(int(tn + fn), state_count),
                "alerts_per_10_second_state": _rate(alert_count, state_count),
                "alerts_per_minute": _rate(alert_count * 60, state_count * interval_seconds),
                "false_alert_proportion": _rate(int(fp), alert_count),
                "missed_positive_proportion": _rate(int(fn), int(fn + tp)),
                "true_positive_count": int(tp),
                "false_positive_count": int(fp),
                "true_negative_count": int(tn),
                "false_negative_count": int(fn),
            }
        )
    return rows


def load_policy(path: str | Path) -> dict[str, Any]:
    """Load and minimally validate the checked-in operating policy."""

    policy = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(policy, dict):
        raise ValueError("operating policy must be a YAML mapping")
    modes = policy.get("modes")
    if not isinstance(modes, dict) or set(modes) != {"sensitive", "balanced", "conservative"}:
        raise ValueError("policy must define sensitive, balanced, and conservative modes")
    for name, mode in modes.items():
        if not isinstance(mode, dict) or "threshold" not in mode:
            raise ValueError(f"mode {name} must define threshold")
        validate_threshold(mode["threshold"])
    return policy


def policy_decision(score: float, mode: str, policy: dict[str, Any]) -> dict[str, Any]:
    """Return the deterministic UI-facing decision for one forecast score."""

    modes = policy.get("modes", {})
    if mode not in modes:
        raise ValueError(f"unknown operating mode: {mode}")
    threshold = validate_threshold(modes[mode]["threshold"])
    state = classify_score(score, threshold)
    return {
        "mode": mode,
        "score": float(score),
        "threshold": threshold,
        "state": state,
        "label": "Predictive warning" if state == "warning" else "No predictive warning",
    }
