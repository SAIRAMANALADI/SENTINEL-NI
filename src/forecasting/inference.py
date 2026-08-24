"""Stable offline inference for the frozen K=5 forecasting checkpoint."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import yaml

from src.evaluation.feature_ablation import single_sequence_contributions
from src.evaluation.operating_policy import load_policy, policy_decision
from src.models.baseline_preprocessing import BaselinePreprocessor
from src.models.lstm_world_model import load_checkpoint


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHECKPOINT = PROJECT_ROOT / "models" / "lstm_multistep_k5.pt"
DEFAULT_PREPROCESSOR = PROJECT_ROOT / "models" / "baseline_preprocessor.joblib"
DEFAULT_POLICY = PROJECT_ROOT / "configs" / "operating_policy.yaml"
DEFAULT_SCHEMA = PROJECT_ROOT / "configs" / "state_feature_schema.yaml"
TARGET_VERSION = "docs/TARGET_STATE_SPEC.md"
REQUIRED_CONTEXT_COLUMNS = ["timestamp", "capture_day"]


def _load_feature_contract(schema_path: Path) -> tuple[list[str], str]:
    document = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("feature schema must be a YAML mapping")
    columns = document.get("FEATURE_COLUMNS")
    version = document.get("schema_version")
    if not isinstance(columns, list) or len(columns) != 17 or not isinstance(version, str):
        raise ValueError("feature schema must define 17 features and a schema_version")
    if len(set(columns)) != len(columns):
        raise ValueError("feature schema contains duplicate features")
    return [str(column) for column in columns], version


def _validate_sequence(
    sequence: pd.DataFrame,
    feature_columns: list[str],
    expected_length: int,
) -> tuple[pd.DataFrame, pd.Series, str]:
    if not isinstance(sequence, pd.DataFrame):
        raise TypeError("sequence must be a pandas DataFrame")
    if len(sequence) != expected_length:
        raise ValueError(f"sequence must contain exactly {expected_length} states")
    expected_columns = feature_columns + REQUIRED_CONTEXT_COLUMNS
    if list(sequence.columns) != expected_columns:
        missing = [column for column in expected_columns if column not in sequence.columns]
        unexpected = [column for column in sequence.columns if column not in expected_columns]
        if missing:
            raise ValueError(f"sequence is missing required columns: {missing}")
        if unexpected:
            raise ValueError(f"sequence contains unsupported columns: {unexpected}")
        raise ValueError("sequence feature order or context-column order does not match the contract")
    if sequence["capture_day"].isna().any() or sequence["capture_day"].astype(str).nunique() != 1:
        raise ValueError("sequence must contain one non-missing capture_day")
    values = sequence[feature_columns]
    for column in feature_columns:
        if not pd.api.types.is_numeric_dtype(values[column]) or pd.api.types.is_bool_dtype(values[column]):
            raise TypeError(f"feature {column!r} must have a numeric dtype")
    numeric_values = values.to_numpy(dtype="float64")
    if not np.isfinite(numeric_values).all():
        raise ValueError("sequence features contain NaN or Inf")
    timestamps = pd.to_datetime(sequence["timestamp"], errors="coerce", format="mixed")
    if timestamps.isna().any():
        raise ValueError("sequence contains invalid timestamps")
    deltas = timestamps.diff().dropna()
    if not (deltas == pd.Timedelta(seconds=10)).all():
        raise ValueError("timestamps must be strictly ordered at exactly 10-second intervals")
    capture_day = sequence["capture_day"].astype(str).iloc[0]
    if timestamps.dt.strftime("%Y-%m-%d").ne(capture_day).any():
        raise ValueError("every timestamp must belong to capture_day")
    return sequence.copy(), timestamps, capture_day


def _explanation(
    model: torch.nn.Module,
    sequence: np.ndarray,
    feature_columns: list[str],
    forecast_step: int,
    top_n: int,
) -> dict[str, Any]:
    attribution = single_sequence_contributions(
        model,
        sequence,
        feature_columns,
        forecast_step=forecast_step,
        mask_value=0.0,
    )
    top_features = [
        {
            "feature": row["feature"],
            "contribution": float(row["contribution"]),
            "sensitivity": float(row["absolute_contribution"]),
            "time_position": row["time_position"],
            "position_index": int(row["position_index"]),
            "seconds_before_origin": int(row["seconds_before_origin"]),
            "masked_score": float(row["masked_score"]),
        }
        for row in attribution["contributions"][:top_n]
    ]
    by_position: dict[int, dict[str, float]] = {}
    for row in attribution["contributions"]:
        position = int(row["position_index"])
        summary = by_position.setdefault(position, {"signed": 0.0, "absolute": 0.0})
        summary["signed"] += float(row["contribution"])
        summary["absolute"] += float(row["absolute_contribution"])
    temporal_positions = []
    for position, summary in sorted(by_position.items(), key=lambda item: item[1]["absolute"], reverse=True):
        seconds_before_origin = (sequence.shape[0] - 1 - position) * 10
        temporal_positions.append(
            {
                "position_index": position,
                "time_position": "t" if seconds_before_origin == 0 else f"t-{seconds_before_origin}s",
                "seconds_before_origin": seconds_before_origin,
                "signed_contribution": float(summary["signed"]),
                "sensitivity": float(summary["absolute"] / len(feature_columns)),
            }
        )
    return {
        "method": "single feature-position masking to standardized training mean",
        "forecast_step": int(forecast_step),
        "model_score": float(attribution["baseline_score"]),
        "top_features": top_features,
        "temporal_positions": temporal_positions,
        "causal_claim": False,
        "interpretation": "Feature sensitivity describes model-score response and is not causal attribution.",
    }


def predict_network_state_sequence(
    sequence: pd.DataFrame,
    *,
    checkpoint_path: str | Path = DEFAULT_CHECKPOINT,
    preprocessor_path: str | Path = DEFAULT_PREPROCESSOR,
    policy_path: str | Path = DEFAULT_POLICY,
    schema_path: str | Path = DEFAULT_SCHEMA,
    top_n: int = 5,
) -> dict[str, Any]:
    """Validate, preprocess, forecast, apply policy, and explain one sequence."""

    if isinstance(top_n, bool) or not isinstance(top_n, int) or top_n < 1:
        raise ValueError("top_n must be a positive integer")
    total_started = time.perf_counter()

    feature_columns, schema_version = _load_feature_contract(Path(schema_path))
    policy = load_policy(policy_path)
    mode = policy.get("primary_mode")
    if not isinstance(mode, str) or mode not in policy["modes"]:
        raise ValueError("operating policy primary_mode is missing or invalid")

    model_started = time.perf_counter()
    model, checkpoint = load_checkpoint(checkpoint_path, device="cpu")
    model_load_ms = (time.perf_counter() - model_started) * 1000
    if model.config.sequence_length != 10 or model.config.input_size != len(feature_columns):
        raise ValueError("checkpoint dimensions do not match the frozen 10-state, 17-feature contract")
    if model.config.output_size != 5:
        raise ValueError("approved inference checkpoint must produce exactly K=5 outputs")
    checkpoint_features = list(checkpoint.get("feature_columns", []))
    if checkpoint_features != feature_columns:
        raise ValueError("checkpoint feature order does not match the approved feature schema")

    frame, timestamps, capture_day = _validate_sequence(sequence, feature_columns, model.config.sequence_length)
    preprocessor = BaselinePreprocessor.load(preprocessor_path)
    if preprocessor.feature_columns != feature_columns:
        raise ValueError("preprocessing artifact feature order does not match the approved schema")
    preprocessing_started = time.perf_counter()
    transformed = preprocessor.transform(frame)
    transformed_values = np.array(transformed.to_numpy(dtype="float32"), copy=True)
    preprocessing_ms = (time.perf_counter() - preprocessing_started) * 1000

    forecast_started = time.perf_counter()
    with torch.no_grad():
        logits = model(torch.from_numpy(transformed_values).unsqueeze(0))
        scores = torch.sigmoid(logits).cpu().numpy().reshape(-1)
    if not np.isfinite(scores).all() or ((scores < 0) | (scores > 1)).any():
        raise ValueError("model returned non-finite or out-of-range Forecast Scores")
    forecast_ms = (time.perf_counter() - forecast_started) * 1000

    threshold = float(policy["modes"][mode]["threshold"])
    reference_timestamp = timestamps.iloc[-1]
    forecast_rows = []
    for step, score in enumerate(scores, start=1):
        decision = policy_decision(float(score), mode, policy)
        forecast_rows.append(
            {
                "step": step,
                "horizon_seconds": step * 10,
                "timestamp": (reference_timestamp + pd.Timedelta(seconds=step * 10)).isoformat(),
                "score": float(score),
                "warning": bool(decision["state"] == "warning"),
            }
        )

    explanation_started = time.perf_counter()
    explanation = _explanation(model, transformed_values, feature_columns, forecast_step=1, top_n=top_n)
    explanation_ms = (time.perf_counter() - explanation_started) * 1000

    return {
        "model_version": "LSTM-DEVELOPMENT-V1-direct-multistep-K5",
        "model_checkpoint": str(Path(checkpoint_path).resolve()),
        "feature_schema_version": schema_version,
        "target_version": TARGET_VERSION,
        "policy_version": str(policy.get("policy_version", "unknown")),
        "capture_day": capture_day,
        "reference_timestamp": reference_timestamp.isoformat(),
        "forecast_horizon_seconds": 50,
        "forecast": forecast_rows,
        "operating_mode": mode,
        "threshold": threshold,
        "explanation": explanation,
        "timing_ms": {
            "model_load": float(model_load_ms),
            "preprocessing": float(preprocessing_ms),
            "forecast": float(forecast_ms),
            "explanation": float(explanation_ms),
            "total": float((time.perf_counter() - total_started) * 1000),
        },
    }
