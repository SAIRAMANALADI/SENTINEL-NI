"""Structured, model-derived explanation output for frozen checkpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from src.evaluation.feature_ablation import single_sequence_contributions
from src.models.lstm_world_model import load_checkpoint


DEFAULT_CHECKPOINT = Path(__file__).resolve().parents[2] / "models" / "lstm_multistep_k5.pt"
DEFAULT_FEATURE_COLUMNS = [
    "flow_count",
    "byte_sum",
    "packet_sum",
    "mean_duration",
    "median_duration",
    "mean_iat",
    "iat_std",
    "syn_flow_ratio",
    "ack_flow_ratio",
    "rst_flow_ratio",
    "fwd_byte_share",
    "fwd_packet_share",
    "unique_destination_port_count",
    "bytes_per_second",
    "packets_per_second",
    "packet_size_mean",
    "packet_size_std",
]


def explain_prediction(
    sequence: np.ndarray,
    forecast_step: int,
    checkpoint_path: str | Path = DEFAULT_CHECKPOINT,
    top_n: int = 5,
) -> dict[str, Any]:
    """Explain one forecast using deterministic single-cell mean masking.

    The output reports model sensitivity only. It uses the supplied historical
    sequence and checkpoint; it does not read future labels or claim causality.
    """

    if top_n < 1:
        raise ValueError("top_n must be positive")
    values = np.asarray(sequence, dtype="float32")
    if values.ndim != 2 or not np.isfinite(values).all():
        raise ValueError("sequence must be a finite 2D array")
    model, checkpoint = load_checkpoint(checkpoint_path, device="cpu")
    feature_columns = list(checkpoint.get("feature_columns", DEFAULT_FEATURE_COLUMNS))
    expected = (model.config.sequence_length, model.config.input_size)
    if values.shape != expected:
        raise ValueError(f"sequence shape {values.shape} does not match expected {expected}")
    if len(feature_columns) != values.shape[1]:
        raise ValueError("checkpoint feature columns do not match model input size")
    if forecast_step < 1 or forecast_step > model.config.output_size:
        raise ValueError("forecast_step is outside checkpoint output size")

    attribution = single_sequence_contributions(
        model,
        values,
        feature_columns,
        forecast_step,
        mask_value=0.0,
    )
    top_features = [
        {
            "feature": row["feature"],
            "contribution": row["contribution"],
            "time_position": row["time_position"],
            "position_index": row["position_index"],
            "seconds_before_origin": row["seconds_before_origin"],
            "masked_score": row["masked_score"],
        }
        for row in attribution["contributions"][:top_n]
    ]
    position_scores: dict[int, float] = {}
    for row in attribution["contributions"]:
        position_scores[row["position_index"]] = position_scores.get(row["position_index"], 0.0) + row["absolute_contribution"]
    dominant_position = max(position_scores, key=position_scores.get)
    seconds_before_origin = (values.shape[0] - 1 - dominant_position) * 10
    dominant_label = "t" if seconds_before_origin == 0 else f"t-{seconds_before_origin}s"
    return {
        "forecast_step": int(forecast_step),
        "model_score": float(attribution["baseline_score"]),
        "top_features": top_features,
        "temporal_summary": {
            "dominant_time_position": dominant_label,
            "dominant_position_index": int(dominant_position),
            "mean_absolute_contribution": float(position_scores[dominant_position] / len(feature_columns)),
            "method": "single feature-position masking to standardized training mean",
            "causal_claim": False,
        },
        "checkpoint": str(Path(checkpoint_path).resolve()),
        "target_column": checkpoint.get("target_column", "future_attack_state"),
    }
