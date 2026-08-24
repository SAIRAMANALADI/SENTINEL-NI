"""Train the controlled direct multi-step LSTM development models."""

from __future__ import annotations

import argparse
import copy
import json
import platform
import sys
import time
from importlib.metadata import version
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

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
    _write_json,
)
from src.evaluation.world_model_metrics import (  # noqa: E402
    evaluate_binary,
    select_threshold_by_validation,
    threshold_table,
)
from src.forecasting.multistep import DirectMultiOutputLSTM  # noqa: E402
from src.forecasting.windowing import MultiStepSequenceBatch, build_multistep_sequences  # noqa: E402
from src.models.baseline_preprocessing import BaselinePreprocessor  # noqa: E402
from src.models.lstm_world_model import LSTMConfig, save_checkpoint, set_deterministic_seed  # noqa: E402


SEQUENCE_LENGTH = 10
K_VALUES = (1, 3, 5)
FORECAST_INTERVAL_SECONDS = 10
THRESHOLDS = (0.30, 0.40, 0.50, 0.60, 0.70)
RANDOM_SEED = 42
TARGET_DEFINITION = (
    "For step j in 1..K, target[j] is binary_attack_state(t + j * 10 seconds) "
    "within the same capture_day; K=1 equals future_attack_state(t)."
)

DEFAULT_RESULTS = PROJECT_ROOT / "results" / "multistep_metrics.json"
DEFAULT_K1_CONSISTENCY = PROJECT_ROOT / "results" / "K1_CONSISTENCY_CHECK.md"
DEFAULT_DEGRADATION = PROJECT_ROOT / "results" / "MULTISTEP_FORECAST_DEGRADATION.md"
DEFAULT_REPORT = PROJECT_ROOT / "results" / "MULTISTEP_FORECAST_REPORT.md"
DEFAULT_MODEL_DIR = PROJECT_ROOT / "models"
DEFAULT_HISTORY_DIR = PROJECT_ROOT / "results" / "multistep_histories"
DEFAULT_BASELINE_RESULTS = PROJECT_ROOT / "results" / "BASELINE_TEST_RESULTS.json"
DEFAULT_V1_METRICS = PROJECT_ROOT / "results" / "lstm_v1_metrics.json"


def _load_split_frames(
    split_dir: Path,
    feature_columns: list[str],
) -> tuple[dict[str, pd.DataFrame], dict[str, pd.DataFrame]]:
    """Load full state rows and separately retain V1 rows for scaler fitting."""

    frames: dict[str, pd.DataFrame] = {}
    fit_frames: dict[str, pd.DataFrame] = {}
    required = set(feature_columns) | {
        "binary_attack_state",
        "future_attack_state",
        "future_target_available",
        "timestamp",
        "capture_day",
    }
    for split in ("train", "validation", "test"):
        path = split_dir / f"{split}.parquet"
        frame = pd.read_parquet(path)
        missing = sorted(required - set(frame.columns))
        if missing:
            raise ValueError(f"{path} is missing required columns: {missing}")
        days = sorted(frame["capture_day"].astype(str).unique().tolist())
        if days != EXPECTED_DAYS[split]:
            raise ValueError(f"Unexpected {split} capture days: {days}")
        if set(frame["binary_attack_state"].unique()) - {0, 1}:
            raise ValueError(f"{path} contains invalid binary_attack_state values")
        frames[split] = frame
        fit_frames[split] = frame.loc[frame["future_target_available"].astype(bool)].copy()
    return frames, fit_frames


def _transform(frame: pd.DataFrame, preprocessor: BaselinePreprocessor, feature_columns: list[str]) -> pd.DataFrame:
    transformed_features = preprocessor.transform(frame)
    metadata = frame.drop(columns=feature_columns).reset_index(drop=True)
    return pd.concat([metadata, transformed_features.reset_index(drop=True)], axis=1)


def _make_loader(batch: MultiStepSequenceBatch, batch_size: int, seed: int) -> DataLoader:
    dataset = TensorDataset(
        torch.from_numpy(batch.features.astype("float32")),
        torch.from_numpy(batch.targets.astype("float32")),
    )
    generator = torch.Generator(device="cpu")
    generator.manual_seed(seed)
    return DataLoader(dataset, batch_size=batch_size, shuffle=True, generator=generator, num_workers=0)


def _logits_matrix(model: DirectMultiOutputLSTM, inputs: torch.Tensor) -> torch.Tensor:
    logits = model(inputs)
    return logits.unsqueeze(-1) if logits.ndim == 1 else logits


def _evaluate_epoch(
    model: DirectMultiOutputLSTM,
    batch: MultiStepSequenceBatch,
    criterion: nn.Module,
    device: torch.device,
) -> tuple[float, np.ndarray, list[dict[str, Any]]]:
    model.eval()
    with torch.no_grad():
        inputs = torch.from_numpy(batch.features.astype("float32")).to(device)
        targets = torch.from_numpy(batch.targets.astype("float32")).to(device)
        logits = _logits_matrix(model, inputs)
        loss = criterion(logits, targets)
        probabilities = torch.sigmoid(logits).cpu().numpy()
    metrics = [
        evaluate_binary(batch.targets[:, step], probabilities[:, step], threshold=0.5)
        for step in range(batch.targets.shape[1])
    ]
    return float(loss.item()), probabilities, metrics


def _mean_pr_auc(metrics: list[dict[str, Any]]) -> float:
    values = [metric["pr_auc"] for metric in metrics if metric["pr_auc"] is not None]
    if not values:
        raise ValueError("Validation has no usable PR-AUC values")
    return float(np.mean(values))


def _train_one(
    train_batch: MultiStepSequenceBatch,
    validation_batch: MultiStepSequenceBatch,
    config: LSTMConfig,
    positive_weights: np.ndarray,
) -> dict[str, Any]:
    set_deterministic_seed(config.random_seed)
    device = torch.device(config.device)
    model = DirectMultiOutputLSTM(config).to(device)
    weight = torch.from_numpy(positive_weights.astype("float32")).to(device)
    criterion = nn.BCEWithLogitsLoss(pos_weight=weight)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    loader = _make_loader(train_batch, config.batch_size, config.random_seed)
    history: list[dict[str, Any]] = []
    best_state: dict[str, torch.Tensor] | None = None
    best_epoch = 0
    best_score = float("-inf")
    best_loss = float("inf")

    for epoch in range(1, config.epochs + 1):
        model.train()
        total_loss = 0.0
        total_rows = 0
        for inputs, targets in loader:
            inputs = inputs.to(device)
            targets = targets.to(device)
            optimizer.zero_grad(set_to_none=True)
            logits = _logits_matrix(model, inputs)
            loss = criterion(logits, targets)
            if not torch.isfinite(loss):
                raise ValueError(f"Non-finite training loss at epoch {epoch}")
            loss.backward()
            optimizer.step()
            rows = len(targets)
            total_loss += float(loss.item()) * rows
            total_rows += rows
        train_loss = total_loss / total_rows
        validation_loss, _probabilities, validation_metrics = _evaluate_epoch(
            model, validation_batch, criterion, device
        )
        score = _mean_pr_auc(validation_metrics)
        if not np.isfinite([train_loss, validation_loss, score]).all():
            raise ValueError(f"Non-finite loss or validation score at epoch {epoch}")
        if score > best_score:
            best_state = {name: value.detach().cpu().clone() for name, value in model.state_dict().items()}
            best_epoch = epoch
            best_score = score
            best_loss = validation_loss
        history.append(
            {
                "epoch": epoch,
                "train_loss": train_loss,
                "validation_loss": validation_loss,
                "validation_pr_auc_mean": score,
                "validation_pr_auc_by_step": [metric["pr_auc"] for metric in validation_metrics],
                "validation_f1_at_0_5_by_step": [metric["f1"] for metric in validation_metrics],
            }
        )

    if best_state is None:
        raise RuntimeError("No direct multi-step checkpoint was selected")
    model.load_state_dict(best_state)
    best_loss, best_probabilities, best_metrics = _evaluate_epoch(model, validation_batch, criterion, device)
    return {
        "model": model,
        "best_epoch": best_epoch,
        "best_validation_metric": best_score,
        "best_validation_loss": best_loss,
        "best_validation_probabilities": best_probabilities,
        "best_validation_metrics_at_0_5": best_metrics,
        "history": history,
    }


def _positive_weights(batch: MultiStepSequenceBatch) -> np.ndarray:
    weights: list[float] = []
    for step in range(batch.targets.shape[1]):
        positives = int((batch.targets[:, step] == 1).sum())
        negatives = int((batch.targets[:, step] == 0).sum())
        if positives == 0:
            raise ValueError(f"Training horizon {step + 1} has no positive targets")
        weights.append(negatives / positives)
    values = np.asarray(weights, dtype="float64")
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("Training-only positive-class weights are invalid")
    return values


def _metrics_by_step(targets: np.ndarray, probabilities: np.ndarray, thresholds: list[float]) -> list[dict[str, Any]]:
    return [
        evaluate_binary(targets[:, step], probabilities[:, step], thresholds[step])
        for step in range(targets.shape[1])
    ]


def _write_history(history_dir: Path, horizon: int, history: list[dict[str, Any]]) -> dict[str, str]:
    history_dir.mkdir(parents=True, exist_ok=True)
    json_path = history_dir / f"k{horizon}_history.json"
    csv_path = history_dir / f"k{horizon}_history.csv"
    json_path.write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")
    rows = []
    for item in history:
        row = {
            "epoch": item["epoch"],
            "train_loss": item["train_loss"],
            "validation_loss": item["validation_loss"],
            "validation_pr_auc_mean": item["validation_pr_auc_mean"],
        }
        for step, value in enumerate(item["validation_pr_auc_by_step"], start=1):
            row[f"validation_pr_auc_step_{step}"] = value
        for step, value in enumerate(item["validation_f1_at_0_5_by_step"], start=1):
            row[f"validation_f1_at_0_5_step_{step}"] = value
        rows.append(row)
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    return {"json": str(json_path.resolve()), "csv": str(csv_path.resolve())}


def _run_one(
    horizon: int,
    batches: dict[str, MultiStepSequenceBatch],
    feature_columns: list[str],
    schema_version: str,
    model_dir: Path,
    history_dir: Path,
) -> dict[str, Any]:
    train_batch = batches["train"]
    validation_batch = batches["validation"]
    test_batch = batches["test"]
    positive_weights = _positive_weights(train_batch)
    config = LSTMConfig(
        input_size=17,
        hidden_size=64,
        num_layers=1,
        dropout=0.0,
        learning_rate=0.001,
        batch_size=128,
        epochs=20,
        sequence_length=SEQUENCE_LENGTH,
        forecast_horizon=horizon,
        random_seed=RANDOM_SEED,
        device="cpu",
        output_size=horizon,
    )
    started = time.perf_counter()
    training = _train_one(train_batch, validation_batch, config, positive_weights)
    training_seconds = time.perf_counter() - started

    validation_probabilities = training["best_validation_probabilities"]
    threshold_rows: dict[str, list[dict[str, Any]]] = {}
    selected_thresholds: list[float] = []
    for step in range(horizon):
        rows = threshold_table(validation_batch.targets[:, step], validation_probabilities[:, step], THRESHOLDS)
        threshold_rows[str(step + 1)] = rows
        selected_thresholds.append(float(select_threshold_by_validation(rows)["threshold"]))
    validation_metrics = _metrics_by_step(validation_batch.targets, validation_probabilities, selected_thresholds)

    # One test forward pass occurs only after checkpoint and all thresholds are
    # frozen from validation.
    training["model"].eval()
    with torch.no_grad():
        test_logits = _logits_matrix(
            training["model"],
            torch.from_numpy(test_batch.features.astype("float32")),
        )
        test_probabilities = torch.sigmoid(test_logits).cpu().numpy()
    if not np.isfinite(test_probabilities).all():
        raise ValueError(f"Non-finite test probabilities for K={horizon}")
    test_metrics = _metrics_by_step(test_batch.targets, test_probabilities, selected_thresholds)

    checkpoint_path = model_dir / f"lstm_multistep_k{horizon}.pt"
    config_path = model_dir / f"lstm_multistep_k{horizon}_config.json"
    metadata = {
        "experiment": "LSTM-DEVELOPMENT-V1-direct-multistep",
        "development_model": True,
        "model_version": f"LSTM-DEVELOPMENT-V1-direct-multistep-K{horizon}",
        "sequence_length": SEQUENCE_LENGTH,
        "forecast_horizon": horizon,
        "forecast_horizon_steps": horizon,
        "forecast_horizon_seconds": horizon * FORECAST_INTERVAL_SECONDS,
        "state_interval_seconds": FORECAST_INTERVAL_SECONDS,
        "capture_interval_seconds": FORECAST_INTERVAL_SECONDS,
        "input_feature_count": len(feature_columns),
        "feature_schema_version": schema_version,
        "target_version": "docs/TARGET_STATE_SPEC.md",
        "target_definition": TARGET_DEFINITION,
        "train_split": EXPECTED_DAYS["train"],
        "validation_split": EXPECTED_DAYS["validation"],
        "test_split": EXPECTED_DAYS["test"],
        "seed": RANDOM_SEED,
        "target_source_column": "binary_attack_state",
        "loss": "BCEWithLogitsLoss",
        "positive_weights": positive_weights.tolist(),
        "positive_class_weights": positive_weights.tolist(),
        "selected_thresholds": selected_thresholds,
        "checkpoint_selection": "mean validation PR-AUC across forecast steps",
        "checkpoint_selection_metric": "mean validation PR-AUC across forecast steps",
        "threshold_selection": "per-step validation F1",
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
        selected_thresholds[0],
        training["best_epoch"],
        training["best_validation_metric"],
        metadata,
        model_metadata=metadata,
    )
    _write_json(
        config_path,
        {
            **config.to_dict(),
            "development_model": True,
            "feature_columns": feature_columns,
            "target_column": "future_attack_state",
            "target_source_column": "binary_attack_state",
            "target_version": "docs/TARGET_STATE_SPEC.md",
            "model_version": metadata["model_version"],
            "forecast_horizon_steps": metadata["forecast_horizon_steps"],
            "forecast_horizon_seconds": metadata["forecast_horizon_seconds"],
            "state_interval_seconds": metadata["state_interval_seconds"],
            "capture_interval_seconds": metadata["capture_interval_seconds"],
            "input_feature_count": metadata["input_feature_count"],
            "target_definition": metadata["target_definition"],
            "train_split": metadata["train_split"],
            "validation_split": metadata["validation_split"],
            "test_split": metadata["test_split"],
            "seed": metadata["seed"],
            "positive_class_weights": metadata["positive_class_weights"],
            "threshold_selection_split": metadata["threshold_selection_split"],
            "checkpoint_selection_metric": metadata["checkpoint_selection_metric"],
            "feature_schema_version": schema_version,
            "loss": "BCEWithLogitsLoss",
            "positive_weights": positive_weights.tolist(),
            "selected_thresholds": selected_thresholds,
            "checkpoint_selection": "mean validation PR-AUC across forecast steps",
            "threshold_selection": "per-step validation F1",
        },
    )
    history_paths = _write_history(history_dir, horizon, training["history"])
    return {
        "horizon": horizon,
        "development_model": True,
        "config": config.to_dict(),
        "positive_weights": positive_weights.tolist(),
        "sample_counts": {
            split: {
                "sequences": int(len(batch.targets)),
                "positive_by_step": [int((batch.targets[:, step] == 1).sum()) for step in range(horizon)],
                "negative_by_step": [int((batch.targets[:, step] == 0).sum()) for step in range(horizon)],
                "input_shape": list(batch.features.shape),
                "target_shape": list(batch.targets.shape),
            }
            for split, batch in batches.items()
        },
        "best_epoch": int(training["best_epoch"]),
        "best_validation_metric": float(training["best_validation_metric"]),
        "best_validation_loss": float(training["best_validation_loss"]),
        "selected_thresholds": selected_thresholds,
        "threshold_rows": threshold_rows,
        "validation_metrics": validation_metrics,
        "test_metrics": test_metrics,
        "training_seconds": training_seconds,
        "checkpoint": str(checkpoint_path.resolve()),
        "config": str(config_path.resolve()),
        "history": history_paths,
        "threshold_selection_split": "validation",
        "test_used_for_selection": False,
        "test_evaluated_once_after_selection": True,
        "training_history": training["history"],
    }


def _check_k1_alignment(
    raw_frames: dict[str, pd.DataFrame],
    batches: dict[str, MultiStepSequenceBatch],
) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    for split, batch in batches.items():
        frame = raw_frames[split]
        current_source = frame.iloc[batch.target_positions[:, 0]]["binary_attack_state"].to_numpy(dtype="int8")
        approved_target = frame.iloc[batch.input_end_positions]["future_attack_state"].to_numpy(dtype="int8")
        checks[split] = {
            "sequence_count": int(len(batch.targets)),
            "target_vectors_equal_approved_future_target": bool(np.array_equal(current_source, approved_target)),
            "max_absolute_difference": int(np.max(np.abs(current_source - approved_target))) if len(current_source) else 0,
        }
        if not checks[split]["target_vectors_equal_approved_future_target"]:
            raise ValueError(f"K=1 target mismatch in {split} split")
    return {"status": "PASS", "splits": checks, "no_second_shift": True}


def _write_k1_consistency(path: Path, consistency: dict[str, Any], k1_run: dict[str, Any], v1_metrics_path: Path) -> None:
    old = json.loads(v1_metrics_path.read_text(encoding="utf-8"))
    old_validation = old["validation_metrics"]
    old_test = old["test_metrics"]
    new_validation = k1_run["validation_metrics"][0]
    new_test = k1_run["test_metrics"][0]
    metrics = ("precision", "recall", "f1", "pr_auc", "roc_auc", "false_positive_rate")
    validation_diffs = {metric: abs(new_validation[metric] - old_validation[metric]) for metric in metrics}
    test_diffs = {metric: abs(new_test[metric] - old_test[metric]) for metric in metrics}
    same_metrics = all(value <= 1e-8 for value in validation_diffs.values()) and all(value <= 1e-8 for value in test_diffs.values())
    status = "PASS" if consistency["status"] == "PASS" and same_metrics else "FAIL"
    content = f"""# K=1 Consistency Check

Status: **{status}**

The direct K=1 model uses the same L=10 inputs, the same approved `future_attack_state` alignment, the same training-only weighting, architecture, seed, optimizer, checkpoint rule, and threshold grid as LSTM-V1.

## Target alignment

{json.dumps(consistency, indent=2)}

## Metric comparison

| Split | Metric | Existing LSTM-V1 | Direct K=1 | Absolute difference |
|---|---|---:|---:|---:|
"""
    rows = []
    for split, old_metrics, new_metrics, diffs in (
        ("validation", old_validation, new_validation, validation_diffs),
        ("test", old_test, new_test, test_diffs),
    ):
        rows.extend(
            f"| {split} | {metric} | {old_metrics[metric]:.9f} | {new_metrics[metric]:.9f} | {diffs[metric]:.9f} |"
            for metric in metrics
        )
    content += "\n".join(rows)
    content += "\n\nThe final test day was evaluated only after validation checkpoint and threshold selection; it was not used for selection.\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if status != "PASS":
        raise ValueError("K=1 consistency check failed; K=3/K=5 must not proceed")


def _write_degradation(path: Path, runs: list[dict[str, Any]]) -> None:
    k5 = next(run for run in runs if run["horizon"] == 5)
    lines = [
        "# Multistep Forecast Degradation",
        "",
        "Direct multi-output development models use L=10 historical states. The consolidated horizon table below comes from the K=5 model, whose five outputs cover +10s through +50s. K=1 and K=3 were also trained as separate direct-output models.",
        "",
        "| Horizon | Precision | Recall | F1 | PR-AUC | ROC-AUC | FPR |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for step, metrics in enumerate(k5["test_metrics"], start=1):
        lines.append(
            f"| +{step * FORECAST_INTERVAL_SECONDS}s | {metrics['precision']:.6f} | {metrics['recall']:.6f} | {metrics['f1']:.6f} | {metrics['pr_auc']:.6f} | {metrics['roc_auc']:.6f} | {metrics['false_positive_rate']:.6f} |"
        )
    lines.extend(["", "## Per-model coverage", ""])
    for run in runs:
        lines.append(
            f"- K={run['horizon']}: {run['sample_counts']['test']['sequences']:,} test sequences, output shape `{tuple(run['sample_counts']['test']['target_shape'])}`, thresholds `{run['selected_thresholds']}`."
        )
    lines.extend(
        [
            "",
            "These are state-level forecast metrics. No uncertainty estimates or attack-technique predictions are included.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_report(path: Path, result: dict[str, Any], consistency: dict[str, Any]) -> None:
    lines = [
        "# Multistep Forecast Report",
        "",
        "## 1. Input dataset",
        "",
        f"- `{result['input_path']}`",
        "- Frozen V1 network-state pipeline; no data or target changes.",
        "- Final test day 2018-02-28 remained reserved until validation selection completed.",
        "",
        "## 2. Sequence length",
        "",
        "L=10 historical states, representing 100 seconds of context.",
        "",
        "## 3. K values tested",
        "",
        "K=1, K=3, and K=5 using direct multi-output heads.",
        "",
        "## 4. Target construction",
        "",
        "`binary_attack_state` is read from the next K rows inside the same capture day/group. K=1 is checked against the existing `future_attack_state` at the final input row. No second shift is applied.",
        "",
        "## 5. Model architecture",
        "",
        "Development model, not final architecture selection: LSTM encoder (hidden 64, one layer, dropout 0) followed by a linear K-logit direct output head.",
        "",
        "## 6. Training configuration",
        "",
        "- Adam, learning rate 0.001, batch size 128, 20 epochs, seed 42, CPU.",
        "- BCEWithLogitsLoss with one positive-class weight per future step, calculated from training targets only.",
        "- Checkpoint selection: mean validation PR-AUC across steps.",
        "- Threshold selection: per-step validation F1 over thresholds 0.30, 0.40, 0.50, 0.60, 0.70.",
        "",
        "## 7–9. Results",
        "",
        "| K | Train sequences | Validation sequences | Test sequences | Best epoch | Thresholds |",
        "|---:|---:|---:|---:|---:|---|",
    ]
    for run in result["runs"]:
        lines.append(
            f"| {run['horizon']} | {run['sample_counts']['train']['sequences']:,} | {run['sample_counts']['validation']['sequences']:,} | {run['sample_counts']['test']['sequences']:,} | {run['best_epoch']} | {run['selected_thresholds']} |"
        )
    lines.extend(["", "Validation and test metrics are recorded in `results/multistep_metrics.json` and the degradation report.", ""])
    for run in result["runs"]:
        lines.extend(
            [
                f"### K={run['horizon']}",
                "",
                "Validation metrics:",
                "",
                "| Step | Precision | Recall | F1 | PR-AUC | ROC-AUC | FPR |",
                "|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for step, validation in enumerate(run["validation_metrics"], start=1):
            lines.append(
                f"| +{step * FORECAST_INTERVAL_SECONDS}s | {validation['precision']:.6f} | {validation['recall']:.6f} | {validation['f1']:.6f} | {validation['pr_auc']:.6f} | {validation['roc_auc']:.6f} | {validation['false_positive_rate']:.6f} |"
            )
        lines.extend(
            [
                "",
                "Test metrics:",
                "",
                "| Step | Precision | Recall | F1 | PR-AUC | ROC-AUC | FPR | Confusion matrix |",
                "|---:|---:|---:|---:|---:|---:|---:|---|",
            ]
        )
        for step, test in enumerate(run["test_metrics"], start=1):
            lines.append(
                f"| +{step * FORECAST_INTERVAL_SECONDS}s | {test['precision']:.6f} | {test['recall']:.6f} | {test['f1']:.6f} | {test['pr_auc']:.6f} | {test['roc_auc']:.6f} | {test['false_positive_rate']:.6f} | `{test['confusion_matrix']}` |"
            )
        lines.append("")
    lines.extend(
        [
            "## 10. Early-warning analysis",
            "",
            "Not computed as an episode-level lead-time metric. The approved contract defines state-level future attack labels but does not define attack episodes, onset grouping, or a first-warning aggregation rule. No unsupported lead-time claim is made.",
            "",
            "## 11. K=1 consistency",
            "",
            f"{consistency['status']}. See `results/K1_CONSISTENCY_CHECK.md`.",
            "",
            "## 12. Limitations",
            "",
            "- This is a direct multi-output development model, not a final architecture selection.",
            "- No additional unseen capture day exists, so temporal generalization remains unresolved.",
            "- The final test day is limited to one capture day and was not used for model selection.",
            "- The target forecasts binary attack-state presence, not exact attack techniques.",
            "- V1 remains flow-derived and has no verified packet-level enrichment.",
            "",
            "## 13. Recommendation",
            "",
            "Keep the result as a technical multi-step feasibility experiment. Do not promote a final architecture or claim cross-day generalization from this run.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def train_multistep(
    input_path: Path = DEFAULT_INPUT,
    schema_path: Path = DEFAULT_SCHEMA,
    split_dir: Path = DEFAULT_SPLIT_DIR,
    split_report_path: Path = DEFAULT_SPLIT_REPORT,
    results_path: Path = DEFAULT_RESULTS,
    k1_consistency_path: Path = DEFAULT_K1_CONSISTENCY,
    degradation_path: Path = DEFAULT_DEGRADATION,
    report_path: Path = DEFAULT_REPORT,
    model_dir: Path = DEFAULT_MODEL_DIR,
    history_dir: Path = DEFAULT_HISTORY_DIR,
    v1_metrics_path: Path = DEFAULT_V1_METRICS,
) -> dict[str, Any]:
    if not input_path.is_file() or not split_report_path.is_file():
        raise FileNotFoundError("Frozen V1 input or approved split report is missing")
    feature_columns, schema_version = _load_features(schema_path)
    split_report = json.loads(split_report_path.read_text(encoding="utf-8"))
    if split_report.get("split_day_overlap") is not False:
        raise ValueError("Approved split report does not prove day disjointness")
    raw_frames, fit_frames = _load_split_frames(split_dir, feature_columns)
    preprocessor = BaselinePreprocessor(feature_columns)
    preprocessor.fit(fit_frames["train"])
    transformed = {
        split: _transform(raw_frames[split], preprocessor, feature_columns)
        for split in ("train", "validation", "test")
    }
    batches_by_horizon: dict[int, dict[str, MultiStepSequenceBatch]] = {}
    for horizon in K_VALUES:
        batches_by_horizon[horizon] = {
            split: build_multistep_sequences(
                transformed[split],
                feature_columns,
                "binary_attack_state",
                sequence_length=SEQUENCE_LENGTH,
                forecast_horizon=horizon,
            )
            for split in ("train", "validation", "test")
        }
        for split, batch in batches_by_horizon[horizon].items():
            if not np.isfinite(batch.features).all() or not np.isfinite(batch.targets).all():
                raise ValueError(f"Non-finite data in K={horizon} {split} batch")
    k1_alignment = _check_k1_alignment(raw_frames, batches_by_horizon[1])
    runs = [
        _run_one(
            horizon,
            batches_by_horizon[horizon],
            feature_columns,
            schema_version,
            model_dir,
            history_dir,
        )
        for horizon in K_VALUES
    ]
    result = {
        "experiment": "LSTM-DEVELOPMENT-V1-direct-multistep",
        "development_model": True,
        "input_path": str(input_path.resolve()),
        "feature_columns": feature_columns,
        "feature_count": len(feature_columns),
        "sequence_length": SEQUENCE_LENGTH,
        "forecast_interval_seconds": FORECAST_INTERVAL_SECONDS,
        "target_source_column": "binary_attack_state",
        "target_column": "future_attack_state",
        "target_construction": "future source rows at +10s increments; K=1 checked against future_attack_state",
        "horizons": list(K_VALUES),
        "schema_version": schema_version,
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
            "checkpoint_selection": "mean validation PR-AUC",
            "threshold_selection": "per-step validation F1",
            "test_used_for_selection": False,
        },
        "k1_alignment": k1_alignment,
        "runs": runs,
        "artifacts": {
            "k1_consistency": str(k1_consistency_path.resolve()),
            "degradation": str(degradation_path.resolve()),
            "report": str(report_path.resolve()),
        },
    }
    _write_json(results_path, result)
    _write_k1_consistency(k1_consistency_path, k1_alignment, runs[0], v1_metrics_path)
    _write_degradation(degradation_path, runs)
    _write_report(report_path, result, k1_alignment)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--split-dir", type=Path, default=DEFAULT_SPLIT_DIR)
    parser.add_argument("--split-report", type=Path, default=DEFAULT_SPLIT_REPORT)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--k1-consistency", type=Path, default=DEFAULT_K1_CONSISTENCY)
    parser.add_argument("--degradation", type=Path, default=DEFAULT_DEGRADATION)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--history-dir", type=Path, default=DEFAULT_HISTORY_DIR)
    parser.add_argument("--v1-metrics", type=Path, default=DEFAULT_V1_METRICS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = train_multistep(
            input_path=args.input,
            schema_path=args.schema,
            split_dir=args.split_dir,
            split_report_path=args.split_report,
            results_path=args.results,
            k1_consistency_path=args.k1_consistency,
            degradation_path=args.degradation,
            report_path=args.report,
            model_dir=args.model_dir,
            history_dir=args.history_dir,
            v1_metrics_path=args.v1_metrics,
        )
    except (FileNotFoundError, ValueError, TypeError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"K values completed: {result['horizons']}")
    for run in result["runs"]:
        print(
            f"K={run['horizon']} best_epoch={run['best_epoch']} "
            f"thresholds={run['selected_thresholds']} "
            f"training_seconds={run['training_seconds']:.2f}"
        )
    print(f"K=1 consistency: {result['k1_alignment']['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
