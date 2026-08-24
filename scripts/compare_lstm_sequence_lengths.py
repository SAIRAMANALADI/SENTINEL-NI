"""Run the controlled LSTM sequence-length comparison on frozen V1 states."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.train_world_model import (  # noqa: E402
    DEFAULT_INPUT,
    DEFAULT_SCHEMA,
    DEFAULT_SPLIT_DIR,
    DEFAULT_SPLIT_REPORT,
    EXPECTED_DAYS,
    _load_features,
    _load_split,
    _make_loader,
    _train_variant,
    _transform_split,
    _write_json,
)
from src.evaluation.world_model_metrics import (  # noqa: E402
    evaluate_binary,
    select_threshold_by_validation,
    threshold_table,
)
from src.forecasting.windowing import build_sequences  # noqa: E402
from src.models.baseline_preprocessing import BaselinePreprocessor  # noqa: E402
from src.models.lstm_world_model import LSTMConfig, save_checkpoint  # noqa: E402


SEQUENCE_LENGTHS = (5, 10, 20)
THRESHOLDS = (0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70)
FORECAST_HORIZON = 1
RANDOM_SEED = 42

# Keep the controlled comparison identical to the completed LSTM-V1 run.
# This value was calculated from training-only L=10 sequences and is never
# recomputed from validation or test labels.
PRIMARY_POSITIVE_WEIGHT = 4.314590747330961

DEFAULT_RESULTS = PROJECT_ROOT / "results" / "lstm_sequence_length_metrics.json"
DEFAULT_REPORT = PROJECT_ROOT / "results" / "LSTM_SEQUENCE_LENGTH_COMPARISON.md"
DEFAULT_ANALYSIS = PROJECT_ROOT / "docs" / "TEMPORAL_CONTEXT_ANALYSIS.md"
DEFAULT_HISTORY_DIR = PROJECT_ROOT / "results" / "lstm_sequence_histories"
DEFAULT_MODEL_DIR = PROJECT_ROOT / "models"
DEFAULT_BASELINE_RESULTS = PROJECT_ROOT / "results" / "BASELINE_TEST_RESULTS.json"


def make_controlled_config(sequence_length: int) -> LSTMConfig:
    """Return the fixed LSTM-V1 configuration with only length changed."""

    if sequence_length not in SEQUENCE_LENGTHS:
        raise ValueError(f"sequence_length must be one of {SEQUENCE_LENGTHS}")
    return LSTMConfig(
        input_size=17,
        hidden_size=64,
        num_layers=1,
        dropout=0.0,
        learning_rate=1e-3,
        batch_size=128,
        epochs=20,
        sequence_length=sequence_length,
        forecast_horizon=FORECAST_HORIZON,
        random_seed=RANDOM_SEED,
        device="cpu",
    )


def _write_history_files(history_dir: Path, sequence_length: int, history: list[dict[str, Any]]) -> dict[str, str]:
    history_dir.mkdir(parents=True, exist_ok=True)
    json_path = history_dir / f"lstm_l{sequence_length}_history.json"
    csv_path = history_dir / f"lstm_l{sequence_length}_history.csv"
    json_path.write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")
    pd.DataFrame(history).to_csv(csv_path, index=False)
    return {"json": str(json_path.resolve()), "csv": str(csv_path.resolve())}


def _load_and_prepare_batches(
    input_path: Path,
    schema_path: Path,
    split_dir: Path,
    split_report_path: Path,
) -> tuple[list[str], str, dict[int, dict[str, Any]]]:
    if not input_path.is_file() or not split_report_path.is_file():
        raise FileNotFoundError("Frozen V1 input or approved split report is missing")
    feature_columns, schema_version = _load_features(schema_path)
    split_report = json.loads(split_report_path.read_text(encoding="utf-8"))
    if split_report.get("split_day_overlap") is not False:
        raise ValueError("Approved split report does not prove day disjointness")

    frames = {
        name: _load_split(split_dir / f"{name}.parquet", feature_columns)
        for name in ("train", "validation", "test")
    }
    preprocessor = BaselinePreprocessor(feature_columns)
    fitted = preprocessor.fit(frames["train"])
    transformed = {
        "train": _transform_split(frames["train"], fitted, feature_columns),
        "validation": _transform_split(frames["validation"], preprocessor, feature_columns),
        "test": _transform_split(frames["test"], preprocessor, feature_columns),
    }

    batches_by_length: dict[int, dict[str, Any]] = {}
    for sequence_length in SEQUENCE_LENGTHS:
        batches = {
            split: build_sequences(
                frame,
                feature_columns,
                "future_attack_state",
                sequence_length=sequence_length,
                forecast_horizon=FORECAST_HORIZON,
            )
            for split, frame in transformed.items()
        }
        for split, batch in batches.items():
            if batch.features.shape[1:] != (sequence_length, 17):
                raise ValueError(f"Unexpected {split} tensor shape for L={sequence_length}")
            if not np.isfinite(batch.features).all():
                raise ValueError(f"Non-finite {split} tensor for L={sequence_length}")
        batches_by_length[sequence_length] = batches
    return feature_columns, schema_version, batches_by_length


def _sample_counts(batch: Any) -> dict[str, Any]:
    return {
        "sequences": int(len(batch.targets)),
        "positive": int((batch.targets == 1).sum()),
        "negative": int((batch.targets == 0).sum()),
        "input_shape": list(batch.features.shape),
        "target_shape": list(batch.targets.shape),
    }


def _run_one(
    sequence_length: int,
    batches: dict[str, Any],
    feature_columns: list[str],
    schema_version: str,
    model_dir: Path,
    history_dir: Path,
) -> dict[str, Any]:
    config = make_controlled_config(sequence_length)
    train_batch = batches["train"]
    validation_batch = batches["validation"]
    test_batch = batches["test"]

    if PRIMARY_POSITIVE_WEIGHT <= 0 or not np.isfinite(PRIMARY_POSITIVE_WEIGHT):
        raise ValueError("The training-derived positive weight is invalid")
    started = time.perf_counter()
    training = _train_variant(
        train_batch,
        validation_batch,
        config,
        PRIMARY_POSITIVE_WEIGHT,
        weighted=True,
    )
    training_seconds = time.perf_counter() - started

    validation_probabilities = training["best_validation_probabilities"]
    threshold_rows = threshold_table(validation_batch.targets, validation_probabilities, THRESHOLDS)
    selected = select_threshold_by_validation(threshold_rows)
    selected_threshold = float(selected["threshold"])
    validation_metrics = evaluate_binary(
        validation_batch.targets,
        validation_probabilities,
        selected_threshold,
    )

    # This is the only test evaluation for this sequence length, after all
    # validation-based checkpoint and threshold decisions are complete.
    training["model"].eval()
    with torch.no_grad():
        test_logits = training["model"](torch.from_numpy(test_batch.features.astype("float32")))
        test_probabilities = torch.sigmoid(test_logits).cpu().numpy()
    if not np.isfinite(test_probabilities).all():
        raise ValueError(f"Non-finite test probabilities for L={sequence_length}")
    test_metrics = evaluate_binary(test_batch.targets, test_probabilities, selected_threshold)

    checkpoint_path = model_dir / f"lstm_l{sequence_length}_world_model.pt"
    metadata = {
        "experiment": "LSTM-sequence-length-comparison",
        "sequence_length": sequence_length,
        "loss_variant": "training_weighted_bce",
        "positive_weight": PRIMARY_POSITIVE_WEIGHT,
        "threshold_selection_split": "validation",
        "test_used_for_selection": False,
        "test_evaluated_once_after_selection": True,
        "best_epoch": training["best_epoch"],
        "best_validation_metric": training["best_validation_metric"],
        "training_seconds": training_seconds,
        "random_seed": RANDOM_SEED,
    }
    save_checkpoint(
        checkpoint_path,
        training["model"],
        feature_columns,
        "future_attack_state",
        "docs/TARGET_STATE_SPEC.md",
        schema_version,
        selected_threshold,
        training["best_epoch"],
        training["best_validation_metric"],
        metadata,
    )
    history_paths = _write_history_files(history_dir, sequence_length, training["history"])
    return {
        "sequence_length": sequence_length,
        "context_seconds": sequence_length * 10,
        "config": config.to_dict(),
        "positive_weight": PRIMARY_POSITIVE_WEIGHT,
        "sample_counts": {
            split: _sample_counts(batch)
            for split, batch in batches.items()
        },
        "best_epoch": int(training["best_epoch"]),
        "best_validation_metric": float(training["best_validation_metric"]),
        "best_validation_loss": float(training["best_validation_loss"]),
        "selected_threshold": selected_threshold,
        "threshold_rows": threshold_rows,
        "validation_metrics": validation_metrics,
        "test_metrics": test_metrics,
        "training_seconds": training_seconds,
        "checkpoint": str(checkpoint_path.resolve()),
        "history": history_paths,
        "threshold_selection_split": "validation",
        "test_used_for_selection": False,
        "test_evaluated_once_after_selection": True,
        "training_history": training["history"],
    }


def _metric_value(run: dict[str, Any], split: str, metric: str) -> float:
    value = run[f"{split}_metrics"][metric]
    return float(value) if value is not None else float("nan")


def _overfitting_note(run: dict[str, Any]) -> str:
    history = run["training_history"]
    best_epoch = run["best_epoch"]
    final = history[-1]
    best_validation_loss = run["best_validation_loss"]
    best_pr_auc = run["best_validation_metric"]
    final_pr_auc = final["validation_pr_auc"]
    loss_rise = final["validation_loss"] > best_validation_loss
    pr_auc_drop = final_pr_auc < best_pr_auc
    train_loss_drop = final["train_loss"] < history[best_epoch - 1]["train_loss"]
    if best_epoch < len(history) and loss_rise and pr_auc_drop and train_loss_drop:
        return (
            f"Evidence of overfitting after epoch {best_epoch}: training loss continued to fall, "
            "while validation loss rose and validation PR-AUC fell."
        )
    if best_epoch < len(history) and pr_auc_drop:
        return f"Validation PR-AUC peaked at epoch {best_epoch} and declined afterward; overfitting signal is limited."
    return "No clear post-selection overfitting signal in the recorded loss/PR-AUC history."


def _recommendation(runs: list[dict[str, Any]]) -> str:
    # A winner must not trade away any of the early-warning decision metrics:
    # validation F1, PR-AUC, recall, and false-positive rate. Ties or metric
    # trade-offs are deliberately reported as no clear winner.
    candidates = []
    for run in runs:
        val_f1 = _metric_value(run, "validation", "f1")
        val_pr_auc = _metric_value(run, "validation", "pr_auc")
        val_recall = _metric_value(run, "validation", "recall")
        val_fpr = _metric_value(run, "validation", "false_positive_rate")
        if all(
            val_f1 >= _metric_value(other, "validation", "f1")
            and val_pr_auc >= _metric_value(other, "validation", "pr_auc")
            and val_recall >= _metric_value(other, "validation", "recall")
            and val_fpr <= _metric_value(other, "validation", "false_positive_rate")
            for other in runs
        ) and any(
            val_f1 > _metric_value(other, "validation", "f1")
            or val_pr_auc > _metric_value(other, "validation", "pr_auc")
            or val_recall > _metric_value(other, "validation", "recall")
            or val_fpr < _metric_value(other, "validation", "false_positive_rate")
            for other in runs
        ):
            candidates.append(run)
    if len(candidates) == 1:
        return f"LSTM-V2-L{candidates[0]['sequence_length']}"
    return "NO CLEAR WINNER"


def _write_comparison_report(path: Path, runs: list[dict[str, Any]], recommendation: str) -> None:
    lines = [
        "# LSTM Sequence-Length Comparison",
        "",
        "Controlled weighted-BCE comparison using the frozen V1 input, target, split, architecture, optimizer, seed, and training budget. The only independent variable is sequence length.",
        "",
        "| Sequence | Val F1 | Val PR-AUC | Val ROC-AUC | Test F1 | Test PR-AUC | Test ROC-AUC | Test Recall | Test FPR |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for run in runs:
        lines.append(
            f"| {run['sequence_length']} | {_metric_value(run, 'validation', 'f1'):.6f} | "
            f"{_metric_value(run, 'validation', 'pr_auc'):.6f} | {_metric_value(run, 'validation', 'roc_auc'):.6f} | "
            f"{_metric_value(run, 'test', 'f1'):.6f} | {_metric_value(run, 'test', 'pr_auc'):.6f} | "
            f"{_metric_value(run, 'test', 'roc_auc'):.6f} | {_metric_value(run, 'test', 'recall'):.6f} | "
            f"{_metric_value(run, 'test', 'false_positive_rate'):.6f} |"
        )
    lines.extend(["", "## Run details", ""])
    for run in runs:
        validation = run["validation_metrics"]
        test = run["test_metrics"]
        lines.extend(
            [
                f"### L={run['sequence_length']} ({run['context_seconds']} seconds)",
                "",
                f"- Train/validation/test sequences: {run['sample_counts']['train']['sequences']:,} / {run['sample_counts']['validation']['sequences']:,} / {run['sample_counts']['test']['sequences']:,}",
                f"- Tensor shape: `{tuple(run['sample_counts']['train']['input_shape'])}` train; target shape `{tuple(run['sample_counts']['train']['target_shape'])}`",
                f"- Positive weight: `{run['positive_weight']:.12f}`; best epoch: `{run['best_epoch']}`",
                f"- Selected threshold: `{run['selected_threshold']:.2f}`; training time: `{run['training_seconds']:.2f}` seconds",
                f"- Validation precision/recall/F1/PR-AUC/ROC-AUC/FPR: `{validation['precision']:.6f}` / `{validation['recall']:.6f}` / `{validation['f1']:.6f}` / `{validation['pr_auc']:.6f}` / `{validation['roc_auc']:.6f}` / `{validation['false_positive_rate']:.6f}`",
                f"- Test precision/recall/F1/PR-AUC/ROC-AUC/FPR: `{test['precision']:.6f}` / `{test['recall']:.6f}` / `{test['f1']:.6f}` / `{test['pr_auc']:.6f}` / `{test['roc_auc']:.6f}` / `{test['false_positive_rate']:.6f}`",
                f"- Test confusion matrix: `{test['confusion_matrix']}`",
                f"- Checkpoint: `{run['checkpoint']}`",
                f"- Histories: `{run['history']['json']}` and `{run['history']['csv']}`",
                "",
                "Validation threshold table:",
                "",
                "| Threshold | Precision | Recall | F1 | FPR |",
                "|---:|---:|---:|---:|---:|",
            ]
        )
        lines.extend(
            f"| {row['threshold']:.2f} | {row['precision']:.6f} | {row['recall']:.6f} | {row['f1']:.6f} | {row['false_positive_rate']:.6f} |"
            for row in run["threshold_rows"]
        )
        lines.append("")
    lines.extend(
        [
            "## Decision",
            "",
            f"Recommended model version: **{recommendation}**",
            "",
            "The test set was evaluated once per sequence length only after validation checkpoint and threshold selection. It was not used to select the recommendation.",
            "",
            "Training and validation histories were saved as CSV/JSON; no visualization dependency was added.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_context_analysis(
    path: Path,
    runs: list[dict[str, Any]],
    recommendation: str,
    baseline_results_path: Path,
) -> None:
    baseline = json.loads(baseline_results_path.read_text(encoding="utf-8"))["final_test_metrics"]
    val_pr = [(_metric_value(run, "validation", "pr_auc"), run["sequence_length"]) for run in runs]
    val_roc = [(_metric_value(run, "validation", "roc_auc"), run["sequence_length"]) for run in runs]
    val_recall = [(_metric_value(run, "validation", "recall"), run["sequence_length"]) for run in runs]
    val_f1 = [(_metric_value(run, "validation", "f1"), run["sequence_length"]) for run in runs]
    best_pr = max(val_pr)
    best_roc = max(val_roc)
    best_recall = max(val_recall)
    best_f1 = max(val_f1)
    longer_pr = val_pr[-1][0] > val_pr[0][0]
    longer_roc = val_roc[-1][0] > val_roc[0][0]
    longer_recall = val_recall[-1][0] > val_recall[0][0]
    longer_f1 = val_f1[-1][0] > val_f1[0][0]
    lines = [
        "# Temporal Context Analysis",
        "",
        "This analysis uses the controlled LSTM-L5/L10/L20 comparison. All runs use the frozen V1 features, target, day-aware split, architecture, optimizer, seed, weighted BCE, and validation-only selection.",
        "",
        "## Answers",
        "",
        f"1. Does longer context improve PR-AUC? **{'Yes' if longer_pr else 'No'}** from L=5 to L=20. Best validation PR-AUC is **{best_pr[0]:.6f}** at L={best_pr[1]}.",
        f"2. Does longer context improve ROC-AUC? **{'Yes' if longer_roc else 'No'}** from L=5 to L=20. Best validation ROC-AUC is **{best_roc[0]:.6f}** at L={best_roc[1]}.",
        f"3. Does longer context improve recall? **{'Yes' if longer_recall else 'No'}** from L=5 to L=20. Best validation recall is **{best_recall[0]:.6f}** at L={best_recall[1]}.",
        f"4. Does longer context improve F1? **{'Yes' if longer_f1 else 'No'}** from L=5 to L=20. Best validation F1 is **{best_f1[0]:.6f}** at L={best_f1[1]}.",
        "5. Is there evidence of overfitting?",
    ]
    lines.extend(f"   - L={run['sequence_length']}: {_overfitting_note(run)}" for run in runs)
    lines.extend(
        [
            f"6. Does performance deteriorate as sequence length increases? **{'Yes' if not (longer_pr or longer_roc or longer_recall or longer_f1) else 'Not uniformly'}**. The metric-by-metric results show whether any gain is consistent across early-warning metrics.",
            f"7. Which sequence length should become LSTM-V2? **{recommendation}**.",
            "8. Is the improvement large enough to justify moving forward? **No automatic promotion is justified by this comparison alone**. The decision must consider PR-AUC, recall, F1, and FPR together rather than ROC-AUC alone.",
            "",
            "## Baseline context",
            "",
            f"Logistic Regression test reference: F1 `{baseline['f1']:.6f}`, PR-AUC `{baseline['pr_auc']:.6f}`, recall `{baseline['recall']:.6f}`, FPR `{baseline['false_positive_rate']:.6f}`.",
            "",
            "The comparison is an early-warning benchmark, not deployment evidence. The target remains next 10-second malicious-state presence, and the V1 data remains flow-derived with limited temporal/scenario diversity.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def compare_sequence_lengths(
    input_path: Path = DEFAULT_INPUT,
    schema_path: Path = DEFAULT_SCHEMA,
    split_dir: Path = DEFAULT_SPLIT_DIR,
    split_report_path: Path = DEFAULT_SPLIT_REPORT,
    results_path: Path = DEFAULT_RESULTS,
    report_path: Path = DEFAULT_REPORT,
    analysis_path: Path = DEFAULT_ANALYSIS,
    history_dir: Path = DEFAULT_HISTORY_DIR,
    model_dir: Path = DEFAULT_MODEL_DIR,
    baseline_results_path: Path = DEFAULT_BASELINE_RESULTS,
) -> dict[str, Any]:
    feature_columns, schema_version, batches_by_length = _load_and_prepare_batches(
        input_path,
        schema_path,
        split_dir,
        split_report_path,
    )
    runs = [
        _run_one(
            sequence_length,
            batches_by_length[sequence_length],
            feature_columns,
            schema_version,
            model_dir,
            history_dir,
        )
        for sequence_length in SEQUENCE_LENGTHS
    ]
    recommendation = _recommendation(runs)
    result = {
        "experiment": "LSTM-sequence-length-comparison",
        "input_path": str(input_path.resolve()),
        "feature_columns": feature_columns,
        "feature_count": len(feature_columns),
        "target_column": "future_attack_state",
        "forecast_horizon": FORECAST_HORIZON,
        "sequence_lengths": list(SEQUENCE_LENGTHS),
        "thresholds": list(THRESHOLDS),
        "controls": {
            "hidden_size": 64,
            "num_layers": 1,
            "dropout": 0.0,
            "learning_rate": 0.001,
            "batch_size": 128,
            "epochs": 20,
            "random_seed": RANDOM_SEED,
            "device": "cpu",
            "loss": "BCEWithLogitsLoss",
            "positive_weight": PRIMARY_POSITIVE_WEIGHT,
            "checkpoint_selection": "validation PR-AUC",
            "threshold_selection": "validation F1",
            "test_used_for_selection": False,
        },
        "schema_version": schema_version,
        "runs": runs,
        "recommendation": recommendation,
        "artifacts": {
            "comparison_report": str(report_path.resolve()),
            "context_analysis": str(analysis_path.resolve()),
            "history_directory": str(history_dir.resolve()),
        },
    }
    _write_json(results_path, result)
    _write_comparison_report(report_path, runs, recommendation)
    _write_context_analysis(analysis_path, runs, recommendation, baseline_results_path)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--split-dir", type=Path, default=DEFAULT_SPLIT_DIR)
    parser.add_argument("--split-report", type=Path, default=DEFAULT_SPLIT_REPORT)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--analysis", type=Path, default=DEFAULT_ANALYSIS)
    parser.add_argument("--history-dir", type=Path, default=DEFAULT_HISTORY_DIR)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--baseline-results", type=Path, default=DEFAULT_BASELINE_RESULTS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = compare_sequence_lengths(
            input_path=args.input,
            schema_path=args.schema,
            split_dir=args.split_dir,
            split_report_path=args.split_report,
            results_path=args.results,
            report_path=args.report,
            analysis_path=args.analysis,
            history_dir=args.history_dir,
            model_dir=args.model_dir,
            baseline_results_path=args.baseline_results,
        )
    except (FileNotFoundError, ValueError, TypeError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Sequence lengths: {result['sequence_lengths']}")
    for run in result["runs"]:
        test = run["test_metrics"]
        print(
            f"L={run['sequence_length']} best_epoch={run['best_epoch']} "
            f"threshold={run['selected_threshold']:.2f} "
            f"test_f1={test['f1']:.6f} test_pr_auc={test['pr_auc']:.6f} "
            f"seconds={run['training_seconds']:.2f}"
        )
    print(f"Recommendation: {result['recommendation']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
