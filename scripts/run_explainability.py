"""Run frozen-checkpoint explainability and forecast diagnostics."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.train_multistep import (  # noqa: E402
    DEFAULT_INPUT,
    DEFAULT_SCHEMA,
    DEFAULT_SPLIT_DIR,
    DEFAULT_SPLIT_REPORT,
    SEQUENCE_LENGTH,
    _load_split_frames,
    _load_features,
    _transform,
)
from src.evaluation.feature_ablation import (  # noqa: E402
    FEATURE_GROUPS,
    model_scores,
    run_ablation,
)
from src.evaluation.prediction_diagnostics import (  # noqa: E402
    calibration_bins,
    compare_split_scores,
    score_summary,
    threshold_diagnostics,
)
from src.forecasting.explanation import explain_prediction  # noqa: E402
from src.forecasting.windowing import build_multistep_sequences  # noqa: E402
from src.evaluation.world_model_metrics import evaluate_binary  # noqa: E402
from src.models.baseline_preprocessing import BaselinePreprocessor  # noqa: E402
from src.models.lstm_world_model import load_checkpoint  # noqa: E402


FEATURE_COLUMNS = [
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
K5_CHECKPOINT = PROJECT_ROOT / "models" / "lstm_multistep_k5.pt"
K3_CHECKPOINT = PROJECT_ROOT / "models" / "lstm_multistep_k3.pt"
K5_THRESHOLD_STEP1 = 0.30
DIAGNOSTIC_SAMPLE_LIMIT = 512
THRESHOLDS = (0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70)

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "results"


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _prepare() -> tuple[dict[str, pd.DataFrame], dict[str, Any]]:
    feature_columns, schema_version = _load_features(DEFAULT_SCHEMA)
    if feature_columns != FEATURE_COLUMNS:
        raise ValueError("Feature schema differs from the explainability feature contract")
    split_report = json.loads(DEFAULT_SPLIT_REPORT.read_text(encoding="utf-8"))
    if split_report.get("split_day_overlap") is not False:
        raise ValueError("Split report does not prove day disjointness")
    raw_frames, fit_frames = _load_split_frames(DEFAULT_SPLIT_DIR, feature_columns)
    preprocessor = BaselinePreprocessor(feature_columns)
    preprocessor.fit(fit_frames["train"])
    transformed = {
        split: _transform(raw_frames[split], preprocessor, feature_columns)
        for split in ("train", "validation", "test")
    }
    batches = {
        split: build_multistep_sequences(
            transformed[split],
            feature_columns,
            "binary_attack_state",
            sequence_length=SEQUENCE_LENGTH,
            forecast_horizon=5,
        )
        for split in ("train", "validation", "test")
    }
    return raw_frames, {
        "feature_columns": feature_columns,
        "schema_version": schema_version,
        "preprocessor": preprocessor,
        "transformed": transformed,
        "batches": batches,
    }


def _trajectory_summary(scores: np.ndarray) -> dict[str, Any]:
    values = np.asarray(scores, dtype="float64")
    if values.ndim != 2 or values.shape[1] < 2:
        raise ValueError("trajectory scores must have shape (N, horizon>=2)")
    diffs = np.diff(values, axis=1)
    positive = diffs > 1e-9
    negative = diffs < -1e-9
    increasing = positive.any(axis=1) & ~negative.any(axis=1)
    decreasing = negative.any(axis=1) & ~positive.any(axis=1)
    oscillating = positive.any(axis=1) & negative.any(axis=1)
    unstable = np.max(np.abs(diffs), axis=1) >= 0.25
    return {
        "sample_count": int(len(values)),
        "mean_score_by_step": np.mean(values, axis=0).tolist(),
        "median_score_by_step": np.median(values, axis=0).tolist(),
        "mean_absolute_step_change": np.mean(np.abs(diffs), axis=0).tolist(),
        "monotonically_increasing_count": int(increasing.sum()),
        "monotonically_increasing_rate": float(increasing.mean()),
        "monotonically_decreasing_count": int(decreasing.sum()),
        "monotonically_decreasing_rate": float(decreasing.mean()),
        "oscillating_count": int(oscillating.sum()),
        "oscillating_rate": float(oscillating.mean()),
        "unstable_count": int(unstable.sum()),
        "unstable_rate": float(unstable.mean()),
        "unstable_definition": "maximum adjacent score change >= 0.25",
    }


def _representative_error_cases(
    model: Any,
    batch: Any,
    scores: np.ndarray,
    raw_validation: pd.DataFrame,
) -> list[dict[str, Any]]:
    labels = batch.targets[:, 0].astype("int8")
    predictions = (scores[:, 0] >= K5_THRESHOLD_STEP1).astype("int8")
    categories = {
        "true_positive": (labels == 1) & (predictions == 1),
        "true_negative": (labels == 0) & (predictions == 0),
        "false_positive": (labels == 0) & (predictions == 1),
        "false_negative": (labels == 1) & (predictions == 0),
    }
    cases = []
    for category, mask in categories.items():
        indices = np.flatnonzero(mask)
        if not len(indices):
            cases.append({"category": category, "available": False})
            continue
        if category in {"true_positive", "false_positive", "false_negative"}:
            index = int(indices[np.argmax(scores[indices, 0])])
        else:
            index = int(indices[np.argmin(scores[indices, 0])])
        explanation = explain_prediction(
            batch.features[index],
            forecast_step=1,
            checkpoint_path=K5_CHECKPOINT,
            top_n=5,
        )
        end_position = int(batch.input_end_positions[index])
        start_position = end_position - SEQUENCE_LENGTH + 1
        raw_sequence = raw_validation.iloc[start_position : end_position + 1]
        recent = raw_sequence.iloc[-3:]
        recent_features = [
            row["feature"] for row in explanation["top_features"][:3]
        ]
        trajectory = []
        for row_index, (_, row) in enumerate(recent.iterrows()):
            trajectory.append(
                {
                    "time_position": f"t-{(len(recent) - 1 - row_index) * 10}s" if row_index < len(recent) - 1 else "t",
                    "timestamp": str(row["timestamp"]),
                    "standardized_values_for_top_features": {
                        feature: float(batch.features[index, SEQUENCE_LENGTH - len(recent) + row_index, FEATURE_COLUMNS.index(feature)])
                        for feature in recent_features
                    },
                }
            )
        cases.append(
            {
                "category": category,
                "available": True,
                "validation_sequence_index": index,
                "origin_timestamp": str(batch.origins[index]),
                "target_timestamp_plus_10s": str(batch.target_times[index, 0]),
                "target": int(labels[index]),
                "model_score": float(scores[index, 0]),
                "selected_threshold": K5_THRESHOLD_STEP1,
                "predicted_state": int(predictions[index]),
                "top_contributing_features": explanation["top_features"],
                "recent_state_trajectory": trajectory,
            }
        )
    return cases


def _write_ablation_report(path: Path, ablation: dict[str, Any]) -> None:
    lines = [
        "# Feature Ablation Report",
        "",
        "Checkpoint: `models/lstm_multistep_k5.pt`, forecast step +10s. Evaluation uses the first 512 validation sequences in deterministic order. No retraining was performed.",
        "",
        f"Method: **{ablation['method']}**. Masking replaces selected standardized input cells with `{ablation['mask_value']}`.",
        "",
        f"Baseline validation F1: `{ablation['baseline_metrics']['f1']:.6f}`; PR-AUC: `{ablation['baseline_metrics']['pr_auc']:.6f}`; ROC-AUC: `{ablation['baseline_metrics']['roc_auc']:.6f}`; FPR: `{ablation['baseline_metrics']['false_positive_rate']:.6f}`.",
        "",
        "## Feature importance",
        "",
        "Positive score change means the unmasked feature produced a higher score than its masked version. This is model sensitivity, not causality.",
        "",
        "| Feature | Mean signed score change | Mean absolute score change | ΔF1 | ΔPR-AUC |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in ablation["feature_importance"]:
        lines.append(
            f"| `{row['feature']}` | {row['mean_signed_score_change']:.8f} | {row['mean_absolute_score_change']:.8f} | {row['metric_change']['delta_f1']:.6f} | {row['metric_change']['delta_pr_auc']:.6f} |"
        )
    lines.extend(["", "## Feature-group ablation", "", "| Group | Features | Mean absolute score change | ΔF1 | ΔPR-AUC |", "|---|---|---:|---:|---:|"])
    for row in ablation["group_importance"]:
        lines.append(
            f"| `{row['group']}` | {', '.join(row['features'])} | {row['mean_absolute_score_change']:.8f} | {row['metric_change']['delta_f1']:.6f} | {row['metric_change']['delta_pr_auc']:.6f} |"
        )
    lines.extend(["", "The ranking identifies which inputs the frozen model is sensitive to under this validation sample and masking method. It does not establish that any feature causes the target state."])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_temporal_report(path: Path, ablation: dict[str, Any]) -> None:
    rows = sorted(ablation["temporal_position_importance"], key=lambda row: row["position_index"])
    lines = [
        "# Temporal Attribution Report",
        "",
        "Temporal position attribution uses the same K=5 +10s validation sample and deterministic mean-mask ablation as the feature report.",
        "",
        "| Position | Mean signed score change | Mean absolute score change | ΔF1 | ΔPR-AUC |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| `{row['time_position']}` | {row['mean_signed_score_change']:.8f} | {row['mean_absolute_score_change']:.8f} | {row['metric_change']['delta_f1']:.6f} | {row['metric_change']['delta_pr_auc']:.6f} |"
        )
    dominant = max(rows, key=lambda row: row["mean_absolute_score_change"])
    lines.extend(
        [
            "",
            f"The largest measured mean absolute position sensitivity was `{dominant['time_position']}` ({dominant['mean_absolute_score_change']:.8f}). This is an attribution result for the frozen model, not evidence that the model has learned a causal temporal mechanism.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_diagnostics_report(path: Path, diagnostics: dict[str, Any]) -> None:
    lines = [
        "# Prediction Diagnostics",
        "",
        "Diagnostics use the frozen K=5 direct-output checkpoint. Validation is used for threshold interpretation; test distributions are reported descriptively only and are not used for tuning.",
        "",
    ]
    for step, data in diagnostics["steps"].items():
        validation = data["validation"]
        test = data["test"]
        lines.extend(
            [
                f"## Forecast step {step}",
                "",
                "| Split | Count | Positive mean score | Negative mean score | PR-AUC | ROC-AUC | F1 @ 0.30 | FPR @ 0.30 | Brier | ECE |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
                f"| Validation | {validation['summary']['count']} | {validation['summary']['positive_scores']['mean']:.6f} | {validation['summary']['negative_scores']['mean']:.6f} | {validation['metrics_at_threshold']['pr_auc']:.6f} | {validation['metrics_at_threshold']['roc_auc']:.6f} | {validation['metrics_at_threshold']['f1']:.6f} | {validation['metrics_at_threshold']['false_positive_rate']:.6f} | {validation['calibration']['brier_score']:.6f} | {validation['calibration']['expected_calibration_error']:.6f} |",
                f"| Test | {test['summary']['count']} | {test['summary']['positive_scores']['mean']:.6f} | {test['summary']['negative_scores']['mean']:.6f} | {test['metrics_at_threshold']['pr_auc']:.6f} | {test['metrics_at_threshold']['roc_auc']:.6f} | {test['metrics_at_threshold']['f1']:.6f} | {test['metrics_at_threshold']['false_positive_rate']:.6f} | {test['calibration']['brier_score']:.6f} | {test['calibration']['expected_calibration_error']:.6f} |",
                "",
                "Validation threshold sensitivity:",
                "",
                "| Threshold | Precision | Recall | F1 | FPR |",
                "|---:|---:|---:|---:|---:|",
            ]
        )
        for row in data["validation_thresholds"]:
            lines.append(f"| {row['threshold']:.2f} | {row['precision']:.6f} | {row['recall']:.6f} | {row['f1']:.6f} | {row['false_positive_rate']:.6f} |")
        lines.append("")
    lines.extend(
        [
            "## Interpretation",
            "",
            "Raw scores are not called calibrated probabilities. The measured calibration error and Brier score should be read alongside the threshold table. ROC-AUC/PR-AUC describe ranking quality, while F1 and FPR depend on the selected operating threshold; they need not move together.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_error_report(path: Path, cases: list[dict[str, Any]]) -> None:
    lines = [
        "# Validation Error Analysis",
        "",
        "Representative cases are selected from the validation split only using the frozen K=5 +10s model and threshold 0.30. They are descriptive examples, not tuning data.",
        "",
    ]
    for case in cases:
        lines.extend([f"## {case['category']}", ""])
        if not case.get("available"):
            lines.append("No case of this category was present at the selected validation threshold.")
            lines.append("")
            continue
        lines.extend(
            [
                f"- Origin timestamp: `{case['origin_timestamp']}`",
                f"- +10s target timestamp: `{case['target_timestamp_plus_10s']}`",
                f"- Target: `{case['target']}`; model score: `{case['model_score']:.8f}`; threshold: `{case['selected_threshold']:.2f}`; predicted state: `{case['predicted_state']}`",
                "",
                "Top contributing feature-position cells:",
                "",
                "| Feature | Time position | Contribution | Masked score |",
                "|---|---|---:|---:|",
            ]
        )
        for row in case["top_contributing_features"]:
            lines.append(f"| `{row['feature']}` | `{row['time_position']}` | {row['contribution']:.8f} | {row['masked_score']:.8f} |")
        lines.extend(["", "Recent standardized input trajectory for the top three features:", "", "```json", json.dumps(case["recent_state_trajectory"], indent=2), "```", ""])
    lines.append("The examples show model behavior only; they do not identify attack causes or techniques.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_trajectory_report(path: Path, trajectories: dict[str, Any]) -> None:
    lines = [
        "# Forecast Trajectory Analysis",
        "",
        "Trajectory analysis uses validation sequences and frozen K=3/K=5 checkpoints. It does not tune thresholds or use the final test day for selection.",
        "",
    ]
    for model_name, summary in trajectories.items():
        lines.extend(
            [
                f"## {model_name}",
                "",
                "| Step | Mean score | Median score | Mean absolute step change |",
                "|---:|---:|---:|---:|",
            ]
        )
        for step, (mean, median) in enumerate(zip(summary["mean_score_by_step"], summary["median_score_by_step"]), start=1):
            change = "—" if step == 1 else f"{summary['mean_absolute_step_change'][step - 2]:.8f}"
            lines.append(f"| +{step * 10}s | {mean:.8f} | {median:.8f} | {change} |")
        lines.extend(
            [
                "",
                f"- Monotonically increasing: {summary['monotonically_increasing_count']} ({summary['monotonically_increasing_rate']:.4%})",
                f"- Monotonically decreasing: {summary['monotonically_decreasing_count']} ({summary['monotonically_decreasing_rate']:.4%})",
                f"- Oscillating: {summary['oscillating_count']} ({summary['oscillating_rate']:.4%})",
                f"- Unstable under the defined threshold: {summary['unstable_count']} ({summary['unstable_rate']:.4%})",
                "",
            ]
        )
    lines.append("An increasing score across horizons is not interpreted as proof that an attack is progressing; it is only the observed trajectory of the model score for future state outputs.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_summary_report(path: Path, ablation: dict[str, Any], diagnostics: dict[str, Any], cases: list[dict[str, Any]], trajectories: dict[str, Any]) -> None:
    top_features = ablation["feature_importance"][:5]
    top_positions = ablation["temporal_position_importance"][:3]
    available_cases = sum(case.get("available", False) for case in cases)
    path.write_text(
        "\n".join(
            [
                "# Explainability Report",
                "",
                "## Method",
                "",
                "Frozen K=5 direct-output LSTM checkpoint, forecast step +10s, deterministic mean-mask ablation in standardized input space, 512 validation sequences. No retraining or pipeline changes.",
                "",
                "## Feature attribution",
                "",
                "Top measured feature sensitivities by mean absolute score change:",
                "",
                *[f"- `{row['feature']}`: `{row['mean_absolute_score_change']:.8f}`" for row in top_features],
                "",
                "## Temporal attribution",
                "",
                *[f"- `{row['time_position']}`: `{row['mean_absolute_score_change']:.8f}`" for row in top_positions],
                "",
                "## Ablation findings",
                "",
                f"The most sensitive feature group was `{ablation['group_importance'][0]['group']}` under this measured sample and masking method.",
                "",
                "## Calibration findings",
                "",
                "Raw scores are reported as model scores or pre-calibration predicted probabilities. Calibration diagnostics include Brier score and expected calibration error; no post-hoc calibrator was fit because this task does not authorize changing the frozen model or selecting a calibrated deployment model.",
                "",
                "## Error analysis",
                "",
                f"Validation representatives available: {available_cases}/4 categories. See `results/ERROR_ANALYSIS.md`.",
                "",
                "## Forecast trajectories",
                "",
                f"K=3 and K=5 trajectory summaries were measured on validation data. See `results/FORECAST_TRAJECTORY_ANALYSIS.md`.",
                "",
                "## Limitations",
                "",
                "Attributions are sensitivity to masking, not causal effects. The four capture days do not establish cross-day generalization. Packet-level features are unavailable, and the approved target predicts future attack-state presence rather than attack technique or intent.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def run_explainability(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, Any]:
    if not DEFAULT_INPUT.is_file() or not K5_CHECKPOINT.is_file() or not K3_CHECKPOINT.is_file():
        raise FileNotFoundError("Frozen input or K3/K5 checkpoints are missing")
    raw_frames, prepared = _prepare()
    feature_columns = prepared["feature_columns"]
    batches = prepared["batches"]
    k5_model, k5_checkpoint = load_checkpoint(K5_CHECKPOINT, device="cpu")
    k3_model, k3_checkpoint = load_checkpoint(K3_CHECKPOINT, device="cpu")
    validation_batch = batches["validation"]
    test_batch = batches["test"]

    ablation = run_ablation(
        k5_model,
        validation_batch.features,
        validation_batch.targets[:, 0],
        feature_columns,
        threshold=K5_THRESHOLD_STEP1,
        forecast_step=1,
        sample_limit=DIAGNOSTIC_SAMPLE_LIMIT,
    )
    validation_k5_scores = model_scores(k5_model, validation_batch.features)
    test_k5_scores = model_scores(k5_model, test_batch.features)
    validation_k3_scores = model_scores(k3_model, build_multistep_sequences(
        prepared["transformed"]["validation"], feature_columns, "binary_attack_state", SEQUENCE_LENGTH, 3
    ).features)
    test_k3_scores = model_scores(k3_model, build_multistep_sequences(
        prepared["transformed"]["test"], feature_columns, "binary_attack_state", SEQUENCE_LENGTH, 3
    ).features)

    diagnostics_steps: dict[str, Any] = {}
    for step in range(5):
        diagnostics_steps[str(step + 1)] = {
            "validation": {
                "summary": score_summary(validation_batch.targets[:, step], validation_k5_scores[:, step]),
                "calibration": calibration_bins(validation_batch.targets[:, step], validation_k5_scores[:, step]),
                "metrics_at_threshold": evaluate_binary(validation_batch.targets[:, step], validation_k5_scores[:, step], 0.30),
            },
            "test": {
                "summary": score_summary(test_batch.targets[:, step], test_k5_scores[:, step]),
                "calibration": calibration_bins(test_batch.targets[:, step], test_k5_scores[:, step]),
                "metrics_at_threshold": evaluate_binary(test_batch.targets[:, step], test_k5_scores[:, step], 0.30),
            },
            "validation_thresholds": threshold_diagnostics(validation_batch.targets[:, step], validation_k5_scores[:, step], THRESHOLDS),
        }
    diagnostics = {
        "checkpoint": str(K5_CHECKPOINT.resolve()),
        "test_used_for_selection": False,
        "steps": diagnostics_steps,
    }

    cases = _representative_error_cases(k5_model, validation_batch, validation_k5_scores, raw_frames["validation"])
    trajectories = {
        "K=3": _trajectory_summary(validation_k3_scores),
        "K=5": _trajectory_summary(validation_k5_scores),
    }
    results = {
        "feature_ablation": ablation,
        "prediction_diagnostics": diagnostics,
        "error_cases": cases,
        "forecast_trajectories": trajectories,
        "checkpoints": {
            "k3": str(K3_CHECKPOINT.resolve()),
            "k5": str(K5_CHECKPOINT.resolve()),
        },
        "selection_boundary": "validation-only; final-test results are descriptive diagnostics only",
        "feature_groups": FEATURE_GROUPS,
    }
    _write_json(output_dir / "feature_ablation.json", ablation)
    _write_json(output_dir / "prediction_diagnostics.json", diagnostics)
    _write_json(output_dir / "error_analysis.json", cases)
    _write_json(output_dir / "forecast_trajectory_analysis.json", trajectories)
    _write_json(output_dir / "explainability_metrics.json", results)
    _write_ablation_report(output_dir / "FEATURE_ABLATION_REPORT.md", ablation)
    _write_temporal_report(output_dir / "TEMPORAL_ATTRIBUTION_REPORT.md", ablation)
    _write_diagnostics_report(output_dir / "PREDICTION_DIAGNOSTICS.md", diagnostics)
    _write_error_report(output_dir / "ERROR_ANALYSIS.md", cases)
    _write_trajectory_report(output_dir / "FORECAST_TRAJECTORY_ANALYSIS.md", trajectories)
    _write_summary_report(output_dir / "EXPLAINABILITY_REPORT.md", ablation, diagnostics, cases, trajectories)
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = run_explainability(args.output_dir)
    except (FileNotFoundError, ValueError, TypeError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print("Explainability complete")
    print(f"Top feature: {result['feature_ablation']['feature_importance'][0]['feature']}")
    print(f"Top temporal position: {result['feature_ablation']['temporal_position_importance'][0]['time_position']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
