from __future__ import annotations

import numpy as np
import pytest

from src.evaluation.prediction_diagnostics import calibration_bins, score_summary, threshold_diagnostics


def test_prediction_diagnostics_schema_and_calibration() -> None:
    labels = np.array([0, 0, 1, 1], dtype="int8")
    scores = np.array([0.1, 0.2, 0.7, 0.8], dtype="float64")
    summary = score_summary(labels, scores)
    calibration = calibration_bins(labels, scores)
    thresholds = threshold_diagnostics(labels, scores, [0.3, 0.5, 0.7])

    assert summary["count"] == 4
    assert summary["positive_scores"]["count"] == 2
    assert len(calibration["bins"]) == 10
    assert 0 <= calibration["brier_score"] <= 1
    assert len(thresholds) == 3
    assert all("f1" in row and "false_positive_rate" in row for row in thresholds)


def test_prediction_diagnostics_reject_invalid_scores() -> None:
    labels = np.array([0, 1], dtype="int8")
    with pytest.raises(ValueError):
        score_summary(labels, np.array([0.1, np.nan]))
    with pytest.raises(ValueError):
        calibration_bins(labels, np.array([0.1, 1.2]))
