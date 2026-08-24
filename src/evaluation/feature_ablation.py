"""Deterministic masking ablations for sequence-model explanations."""

from __future__ import annotations

from typing import Any, Iterable

import numpy as np
import torch

from src.evaluation.world_model_metrics import evaluate_binary


FEATURE_GROUPS: dict[str, list[str]] = {
    "volume_traffic": [
        "flow_count",
        "byte_sum",
        "packet_sum",
        "bytes_per_second",
        "packets_per_second",
    ],
    "timing": ["mean_duration", "median_duration", "mean_iat", "iat_std"],
    "tcp_behavior": ["syn_flow_ratio", "ack_flow_ratio", "rst_flow_ratio"],
    "forward_backward_ratios": ["fwd_byte_share", "fwd_packet_share"],
    "diversity_fan_out": ["unique_destination_port_count"],
    "packet_size_statistics": ["packet_size_mean", "packet_size_std"],
}


def _as_matrix(logits: torch.Tensor) -> torch.Tensor:
    return logits.unsqueeze(-1) if logits.ndim == 1 else logits


def model_scores(
    model: torch.nn.Module,
    sequences: np.ndarray,
    batch_size: int = 512,
) -> np.ndarray:
    """Return sigmoid model scores with shape ``(N, output_size)``."""

    values = np.asarray(sequences, dtype="float32")
    if values.ndim != 3 or not np.isfinite(values).all():
        raise ValueError("sequences must be a finite 3D array")
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    try:
        device = next(model.parameters()).device
    except StopIteration as exc:
        raise ValueError("model must contain parameters") from exc
    model.eval()
    outputs: list[np.ndarray] = []
    with torch.no_grad():
        for start in range(0, len(values), batch_size):
            batch = torch.from_numpy(values[start : start + batch_size]).to(device)
            outputs.append(torch.sigmoid(_as_matrix(model(batch))).cpu().numpy())
    if not outputs:
        output_size = int(getattr(getattr(model, "config", None), "output_size", 1))
        return np.empty((0, output_size), dtype="float64")
    result = np.concatenate(outputs, axis=0).astype("float64")
    if not np.isfinite(result).all() or ((result < 0) | (result > 1)).any():
        raise ValueError("model returned invalid scores")
    return result


def mask_sequences(
    sequences: np.ndarray,
    feature_indices: Iterable[int] | None = None,
    position_indices: Iterable[int] | None = None,
    mask_value: float | np.ndarray = 0.0,
) -> np.ndarray:
    """Return a copy with selected feature/position cells replaced by ``mask_value``."""

    values = np.asarray(sequences, dtype="float32")
    if values.ndim != 3 or not np.isfinite(values).all():
        raise ValueError("sequences must be a finite 3D array")
    features = list(range(values.shape[2])) if feature_indices is None else list(feature_indices)
    positions = list(range(values.shape[1])) if position_indices is None else list(position_indices)
    if any(index < 0 or index >= values.shape[2] for index in features):
        raise ValueError("feature index is outside the sequence feature dimension")
    if any(index < 0 or index >= values.shape[1] for index in positions):
        raise ValueError("position index is outside the sequence length")
    masked = values.copy()
    masked[:, positions, :][:, :, features] = mask_value
    # Advanced indexing above can return a temporary array; assign explicitly
    # to guarantee the mutation for every NumPy version.
    for position in positions:
        for feature in features:
            masked[:, position, feature] = mask_value
    return masked


def _metric_delta(
    labels: np.ndarray,
    baseline_scores: np.ndarray,
    ablated_scores: np.ndarray,
    threshold: float,
    step: int,
) -> dict[str, Any]:
    baseline = evaluate_binary(labels, baseline_scores[:, step], threshold)
    ablated = evaluate_binary(labels, ablated_scores[:, step], threshold)
    return {
        "baseline": baseline,
        "ablated": ablated,
        "delta_f1": float(ablated["f1"] - baseline["f1"]),
        "delta_pr_auc": float(ablated["pr_auc"] - baseline["pr_auc"]),
        "delta_roc_auc": float(ablated["roc_auc"] - baseline["roc_auc"]),
        "delta_recall": float(ablated["recall"] - baseline["recall"]),
        "delta_false_positive_rate": float(ablated["false_positive_rate"] - baseline["false_positive_rate"]),
    }


def run_ablation(
    model: torch.nn.Module,
    sequences: np.ndarray,
    labels: np.ndarray,
    feature_names: list[str],
    threshold: float,
    forecast_step: int = 1,
    sample_limit: int | None = None,
    mask_value: float = 0.0,
) -> dict[str, Any]:
    """Measure feature, group, and temporal-position masking sensitivity.

    ``forecast_step`` is one-based. The returned score changes are descriptive
    model responses on the supplied sample; they are not causal effects.
    """

    values = np.asarray(sequences, dtype="float32")
    target_values = np.asarray(labels, dtype="int8")
    if values.ndim != 3 or len(values) != len(target_values):
        raise ValueError("sequences and labels must have compatible dimensions")
    if not feature_names or len(feature_names) != values.shape[2]:
        raise ValueError("feature_names must match the sequence feature dimension")
    if forecast_step < 1:
        raise ValueError("forecast_step must be positive and one-based")
    if sample_limit is not None:
        if sample_limit < 1:
            raise ValueError("sample_limit must be positive")
        values = values[:sample_limit]
        target_values = target_values[:sample_limit]
    baseline_scores = model_scores(model, values)
    step = forecast_step - 1
    if step >= baseline_scores.shape[1]:
        raise ValueError("forecast_step exceeds model output size")
    name_to_index = {name: index for index, name in enumerate(feature_names)}
    baseline_metrics = evaluate_binary(target_values, baseline_scores[:, step], threshold)

    feature_rows = []
    for feature_index, feature_name in enumerate(feature_names):
        ablated_scores = model_scores(
            model,
            mask_sequences(values, feature_indices=[feature_index], mask_value=mask_value),
        )
        contribution = baseline_scores[:, step] - ablated_scores[:, step]
        metric_change = _metric_delta(target_values, baseline_scores, ablated_scores, threshold, step)
        feature_rows.append(
            {
                "feature": feature_name,
                "feature_index": feature_index,
                "mean_signed_score_change": float(np.mean(contribution)),
                "mean_absolute_score_change": float(np.mean(np.abs(contribution))),
                "metric_change": metric_change,
            }
        )

    group_rows = []
    for group_name, group_features in FEATURE_GROUPS.items():
        indices = [name_to_index[name] for name in group_features]
        ablated_scores = model_scores(
            model,
            mask_sequences(values, feature_indices=indices, mask_value=mask_value),
        )
        contribution = baseline_scores[:, step] - ablated_scores[:, step]
        metric_change = _metric_delta(target_values, baseline_scores, ablated_scores, threshold, step)
        group_rows.append(
            {
                "group": group_name,
                "features": group_features,
                "mean_signed_score_change": float(np.mean(contribution)),
                "mean_absolute_score_change": float(np.mean(np.abs(contribution))),
                "metric_change": metric_change,
            }
        )

    temporal_rows = []
    for position in range(values.shape[1]):
        ablated_scores = model_scores(
            model,
            mask_sequences(values, position_indices=[position], mask_value=mask_value),
        )
        contribution = baseline_scores[:, step] - ablated_scores[:, step]
        seconds_before_origin = (values.shape[1] - 1 - position) * 10
        temporal_rows.append(
            {
                "position_index": position,
                "time_position": "t" if seconds_before_origin == 0 else f"t-{seconds_before_origin}s",
                "seconds_before_origin": seconds_before_origin,
                "mean_signed_score_change": float(np.mean(contribution)),
                "mean_absolute_score_change": float(np.mean(np.abs(contribution))),
                "metric_change": _metric_delta(target_values, baseline_scores, ablated_scores, threshold, step),
            }
        )

    feature_rows.sort(key=lambda row: row["mean_absolute_score_change"], reverse=True)
    group_rows.sort(key=lambda row: row["mean_absolute_score_change"], reverse=True)
    temporal_rows.sort(key=lambda row: row["mean_absolute_score_change"], reverse=True)
    return {
        "method": "deterministic mean-mask ablation in standardized input space",
        "sample_count": int(len(values)),
        "sequence_length": int(values.shape[1]),
        "feature_count": int(values.shape[2]),
        "forecast_step": int(forecast_step),
        "threshold": float(threshold),
        "mask_value": float(mask_value),
        "baseline_metrics": baseline_metrics,
        "feature_importance": feature_rows,
        "group_importance": group_rows,
        "temporal_position_importance": temporal_rows,
    }


def single_sequence_contributions(
    model: torch.nn.Module,
    sequence: np.ndarray,
    feature_names: list[str],
    forecast_step: int,
    mask_value: float = 0.0,
) -> dict[str, Any]:
    """Return signed feature-position score changes for one explanation."""

    values = np.asarray(sequence, dtype="float32")
    if values.ndim != 2 or not np.isfinite(values).all():
        raise ValueError("sequence must be a finite 2D array")
    if len(feature_names) != values.shape[1]:
        raise ValueError("feature_names must match sequence feature dimension")
    baseline = model_scores(model, values[None, ...])[0]
    step = forecast_step - 1
    if step < 0 or step >= baseline.shape[0]:
        raise ValueError("forecast_step is outside model output size")
    rows = []
    for position in range(values.shape[0]):
        seconds_before_origin = (values.shape[0] - 1 - position) * 10
        time_label = "t" if seconds_before_origin == 0 else f"t-{seconds_before_origin}s"
        for feature_index, feature_name in enumerate(feature_names):
            masked = mask_sequences(values[None, ...], [feature_index], [position], mask_value)
            ablated = model_scores(model, masked)[0, step]
            contribution = float(baseline[step] - ablated)
            rows.append(
                {
                    "feature": feature_name,
                    "feature_index": feature_index,
                    "contribution": contribution,
                    "absolute_contribution": abs(contribution),
                    "time_position": time_label,
                    "position_index": position,
                    "seconds_before_origin": seconds_before_origin,
                    "masked_score": float(ablated),
                }
            )
    rows.sort(key=lambda row: row["absolute_contribution"], reverse=True)
    return {
        "baseline_score": float(baseline[step]),
        "forecast_step": int(forecast_step),
        "contributions": rows,
    }
