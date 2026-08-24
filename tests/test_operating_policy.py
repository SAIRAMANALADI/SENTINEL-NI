"""Tests for validation-only operating-policy helpers and contract."""

from pathlib import Path

import numpy as np
import pytest

from src.evaluation.operating_policy import (
    classify_score,
    compute_threshold_sweep,
    load_policy,
    policy_decision,
)


ROOT = Path(__file__).resolve().parents[1]


def test_threshold_sweep_is_deterministic_and_reports_alert_budget() -> None:
    labels = np.array([0, 1, 0, 1, 0], dtype="int8")
    scores = np.array([0.10, 0.20, 0.30, 0.80, 0.90], dtype="float64")
    first = compute_threshold_sweep(labels, scores, [0.20, 0.50], interval_seconds=10)
    second = compute_threshold_sweep(labels, scores, [0.20, 0.50], interval_seconds=10)
    assert first == second
    assert first[0]["alert_count"] == 4
    assert first[0]["alerts_per_minute"] == pytest.approx(4.8)
    assert first[1]["true_positive_count"] == 1


def test_warning_boundary_is_inclusive() -> None:
    assert classify_score(0.19, 0.19) == "warning"
    assert classify_score(0.189999, 0.19) == "no_warning"


def test_policy_has_three_distinct_modes_and_balanced_primary() -> None:
    policy = load_policy(ROOT / "configs" / "operating_policy.yaml")
    assert policy["selection_split"] == "validation"
    assert policy["test_used_for_selection"] is False
    assert policy["primary_mode"] == "balanced"
    thresholds = [policy["modes"][name]["threshold"] for name in ("sensitive", "balanced", "conservative")]
    assert len(set(thresholds)) == 3
    assert all(0.0 <= threshold <= 1.0 for threshold in thresholds)


def test_policy_decision_exposes_ui_label() -> None:
    policy = load_policy(ROOT / "configs" / "operating_policy.yaml")
    decision = policy_decision(0.19, "balanced", policy)
    assert decision["state"] == "warning"
    assert decision["label"] == "Predictive warning"


def test_policy_selection_code_does_not_reference_final_test_artifact() -> None:
    source = (ROOT / "src" / "evaluation" / "operating_policy.py").read_text(encoding="utf-8")
    assert "test.parquet" not in source
    assert "data/processed/states/test" not in source
