"""Focused tests for the offline Streamlit dashboard boundary."""

import inspect
import json
from pathlib import Path

import pandas as pd

from app import streamlit_app
from src.evaluation.operating_policy import load_policy
from src.forecasting.inference import predict_network_state_sequence


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "samples" / "inference_demo_sequence.csv"


def test_app_module_imports_and_demo_is_loadable() -> None:
    frame = streamlit_app.load_sequence_from_path(SAMPLE)
    assert len(frame) == 10
    assert len(frame.columns) == 19


def test_dashboard_consumes_real_inference_contract() -> None:
    frame = streamlit_app.load_sequence_from_path(SAMPLE)
    result = predict_network_state_sequence(frame)
    assert {"forecast", "threshold", "explanation", "operating_mode"} <= set(result)
    assert len(result["forecast"]) == 5
    assert {"top_features", "temporal_positions"} <= set(result["explanation"])
    json.dumps(result)


def test_dashboard_threshold_matches_policy_source() -> None:
    policy = load_policy(ROOT / "configs" / "operating_policy.yaml")
    result = predict_network_state_sequence(pd.read_csv(SAMPLE))
    assert result["threshold"] == policy["modes"][policy["primary_mode"]]["threshold"]


def test_dashboard_does_not_hard_code_threshold() -> None:
    source = inspect.getsource(streamlit_app)
    assert "0.19" not in source


def test_preview_and_explanation_are_safe_for_expected_result() -> None:
    frame = pd.read_csv(SAMPLE)
    preview = streamlit_app._preview(frame)
    result = predict_network_state_sequence(frame)
    assert preview["sequence_length"] == 10
    assert preview["feature_count"] == 17
    assert isinstance(result["explanation"]["top_features"], list)
    assert isinstance(result["explanation"]["temporal_positions"], list)
