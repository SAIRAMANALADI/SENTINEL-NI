"""Run the controlled LSTM-V1 experiment on frozen network states."""

from __future__ import annotations

import argparse
import copy
import json
import platform
import sys
from importlib.metadata import version
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import yaml
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.world_model_metrics import evaluate_binary, select_threshold_by_validation, threshold_table
from src.forecasting.windowing import build_sequences
from src.models.baseline_preprocessing import BaselinePreprocessor
from src.models.lstm_world_model import LSTMConfig, LSTMWorldModel, save_checkpoint, set_deterministic_seed


DEFAULT_INPUT = PROJECT_ROOT / "data" / "processed" / "cic_ids2018_network_states.parquet"
DEFAULT_SCHEMA = PROJECT_ROOT / "configs" / "state_feature_schema.yaml"
DEFAULT_SPLIT_DIR = PROJECT_ROOT / "data" / "processed" / "states"
DEFAULT_SPLIT_REPORT = PROJECT_ROOT / "results" / "network_state_split_report.json"
DEFAULT_CHECKPOINT = PROJECT_ROOT / "models" / "lstm_world_model.pt"
DEFAULT_CONFIG = PROJECT_ROOT / "models" / "lstm_world_model_config.json"
DEFAULT_METRICS = PROJECT_ROOT / "results" / "lstm_v1_metrics.json"
DEFAULT_METADATA = PROJECT_ROOT / "results" / "lstm_v1_run_metadata.json"
DEFAULT_REPORT = PROJECT_ROOT / "results" / "LSTM_V1_REPORT.md"
DEFAULT_COMPARISON = PROJECT_ROOT / "results" / "BASELINE_VS_LSTM.md"
THRESHOLDS = (0.30, 0.40, 0.50, 0.60, 0.70)
EXPECTED_DAYS = {
    "train": ["2018-02-14", "2018-02-21"],
    "validation": ["2018-02-22"],
    "test": ["2018-02-28"],
}


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _load_features(schema_path: Path) -> tuple[list[str], str]:
    document = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    features = list(document.get("FEATURE_COLUMNS", []))
    if len(features) != 17 or "future_attack_state" not in document.get("TARGET_COLUMNS", []):
        raise ValueError("Frozen V1 schema does not match the expected 17-feature future target contract")
    return features, str(document["schema_version"])


def _load_split(path: Path, feature_columns: list[str]) -> pd.DataFrame:
    frame = pd.read_parquet(path)
    required = set(feature_columns) | {"future_attack_state", "future_target_available", "timestamp", "capture_day"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{path} is missing required columns: {missing}")
    days = sorted(frame["capture_day"].astype(str).unique().tolist())
    if days != EXPECTED_DAYS[path.stem]:
        raise ValueError(f"Unexpected {path.stem} capture days: {days}")
    frame = frame.loc[frame["future_target_available"].astype(bool)].copy()
    if set(frame["future_attack_state"].unique()) - {0, 1}:
        raise ValueError(f"{path} contains invalid future_attack_state values")
    return frame


def _transform_split(frame: pd.DataFrame, preprocessor: BaselinePreprocessor, feature_columns: list[str]) -> pd.DataFrame:
    transformed = frame.copy()
    transformed[feature_columns] = preprocessor.transform(frame)
    return transformed


def _make_loader(batch: Any, batch_size: int, shuffle: bool, seed: int) -> DataLoader:
    dataset = TensorDataset(
        torch.from_numpy(batch.features.astype("float32")),
        torch.from_numpy(batch.targets.astype("float32")),
    )
    generator = torch.Generator(device="cpu")
    generator.manual_seed(seed)
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle, generator=generator, num_workers=0)


def _loss_value(logits: torch.Tensor, target: torch.Tensor, criterion: nn.Module) -> torch.Tensor:
    return criterion(logits, target)


def _evaluate_epoch(
    model: LSTMWorldModel,
    batch: Any,
    criterion: nn.Module,
    device: torch.device,
) -> tuple[float, np.ndarray, dict[str, Any]]:
    model.eval()
    with torch.no_grad():
        inputs = torch.from_numpy(batch.features.astype("float32")).to(device)
        targets = torch.from_numpy(batch.targets.astype("float32")).to(device)
        logits = model(inputs)
        loss = float(_loss_value(logits, targets, criterion).item())
        probabilities = torch.sigmoid(logits).cpu().numpy()
    metrics = evaluate_binary(batch.targets, probabilities, threshold=0.5)
    return loss, probabilities, metrics


def _train_variant(
    train_batch: Any,
    validation_batch: Any,
    config: LSTMConfig,
    positive_weight: float,
    weighted: bool,
) -> dict[str, Any]:
    set_deterministic_seed(config.random_seed + (0 if weighted else 1000))
    device = torch.device(config.device)
    model = LSTMWorldModel(config).to(device)
    weight = torch.tensor([positive_weight], dtype=torch.float32, device=device) if weighted else None
    criterion = nn.BCEWithLogitsLoss(pos_weight=weight)
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    loader = _make_loader(train_batch, config.batch_size, shuffle=True, seed=config.random_seed + (0 if weighted else 1000))
    history: list[dict[str, Any]] = []
    best_state: dict[str, torch.Tensor] | None = None
    best_epoch = 0
    best_score = float("-inf")
    best_f1 = float("-inf")
    best_validation_loss = float("inf")

    for epoch in range(1, config.epochs + 1):
        model.train()
        total_loss = 0.0
        total_rows = 0
        for inputs, targets in loader:
            inputs = inputs.to(device)
            targets = targets.to(device)
            optimizer.zero_grad(set_to_none=True)
            logits = model(inputs)
            loss = _loss_value(logits, targets, criterion)
            if not torch.isfinite(loss):
                raise ValueError(f"Non-finite training loss at epoch {epoch}")
            loss.backward()
            optimizer.step()
            rows = len(targets)
            total_loss += float(loss.item()) * rows
            total_rows += rows
        train_loss = total_loss / total_rows
        validation_loss, _probabilities, validation_metrics = _evaluate_epoch(model, validation_batch, criterion, device)
        if not np.isfinite([train_loss, validation_loss]).all():
            raise ValueError(f"Non-finite loss at epoch {epoch}")
        score = float(validation_metrics["pr_auc"] if validation_metrics["pr_auc"] is not None else validation_metrics["f1"])
        f1 = float(validation_metrics["f1"])
        if score > best_score or (score == best_score and f1 > best_f1):
            best_state = {name: value.detach().cpu().clone() for name, value in model.state_dict().items()}
            best_epoch = epoch
            best_score = score
            best_f1 = f1
            best_validation_loss = validation_loss
        history.append(
            {
                "epoch": epoch,
                "train_loss": train_loss,
                "validation_loss": validation_loss,
                "validation_pr_auc": validation_metrics["pr_auc"],
                "validation_f1_at_0_5": validation_metrics["f1"],
            }
        )

    if best_state is None:
        raise RuntimeError("No best LSTM checkpoint was selected")
    model.load_state_dict(best_state)
    best_validation_loss, best_probabilities, best_validation_metrics = _evaluate_epoch(model, validation_batch, criterion, device)
    return {
        "model": model,
        "weighted": weighted,
        "positive_weight": positive_weight if weighted else 1.0,
        "best_epoch": best_epoch,
        "best_validation_metric": best_score,
        "best_validation_loss": best_validation_loss,
        "best_validation_probabilities": best_probabilities,
        "best_validation_metrics_at_0_5": best_validation_metrics,
        "history": history,
    }


def _write_lstm_report(path: Path, result: dict[str, Any], baseline: dict[str, Any]) -> None:
    validation = result["validation_metrics"]
    test = result["test_metrics"]
    content = f"""# LSTM-V1 Report

## Configuration

```json
{json.dumps(result['config'], indent=2)}
```

Primary loss: `BCEWithLogitsLoss` with training-derived positive-class weight `{result['positive_weight']:.12f}`. An unweighted BCE control was also trained and compared on validation only.

## Samples

| Split | Sequence samples | Positive | Negative |
|---|---:|---:|---:|
| Train | {result['sample_counts']['train']['sequences']:,} | {result['sample_counts']['train']['positive']:,} | {result['sample_counts']['train']['negative']:,} |
| Validation | {result['sample_counts']['validation']['sequences']:,} | {result['sample_counts']['validation']['positive']:,} | {result['sample_counts']['validation']['negative']:,} |
| Test | {result['sample_counts']['test']['sequences']:,} | {result['sample_counts']['test']['positive']:,} | {result['sample_counts']['test']['negative']:,} |

Input tensor shape: `(N, 10, 17)`  
Target: pre-aligned `future_attack_state`; no second target shift.

## Selection

- Best checkpoint epoch: **{result['best_epoch']}**
- Checkpoint metric: validation PR-AUC
- Selected threshold: **{result['selected_threshold']:.2f}**
- Threshold selection: validation F1 only
- Test used for selection: **No**

## Validation metrics

| Metric | Value |
|---|---:|
| Precision | {validation['precision']:.6f} |
| Recall | {validation['recall']:.6f} |
| F1 | {validation['f1']:.6f} |
| PR-AUC | {validation['pr_auc']:.6f} |
| ROC-AUC | {validation['roc_auc']:.6f} |
| FPR | {validation['false_positive_rate']:.6f} |
| Loss | {result['best_validation_loss']:.6f} |
| Positive support | {validation['positive_support']} |
| Negative support | {validation['negative_support']} |

Confusion matrix: `{validation['confusion_matrix']}`

## Final held-out test metrics

| Metric | Value |
|---|---:|
| Precision | {test['precision']:.6f} |
| Recall | {test['recall']:.6f} |
| F1 | {test['f1']:.6f} |
| PR-AUC | {test['pr_auc']:.6f} |
| ROC-AUC | {test['roc_auc']:.6f} |
| FPR | {test['false_positive_rate']:.6f} |
| Positive support | {test['positive_support']} |
| Negative support | {test['negative_support']} |

Confusion matrix: `{test['confusion_matrix']}`

## BCE comparison

The unweighted and weighted variants were compared using validation only. The weighted variant is the controlled LSTM-V1 primary experiment.

| Variant | Best epoch | Validation PR-AUC @ 0.50 | Validation F1 @ 0.50 |
|---|---:|---:|---:|
| Unweighted BCE | {result['loss_variant_comparison']['unweighted']['best_epoch']} | {result['loss_variant_comparison']['unweighted']['validation_pr_auc']:.6f} | {result['loss_variant_comparison']['unweighted']['validation_f1']:.6f} |
| Training-weighted BCE | {result['loss_variant_comparison']['weighted']['best_epoch']} | {result['loss_variant_comparison']['weighted']['validation_pr_auc']:.6f} | {result['loss_variant_comparison']['weighted']['validation_f1']:.6f} |

## Baseline comparison

See `results/BASELINE_VS_LSTM.md` for the measured comparison. No claim of improvement is made unless the measured metrics support it.

## Limitations

- This is one controlled LSTM experiment, not a tuned model.
- The target is observed malicious-traffic presence, not compromise or an entire attack chain.
- V1 remains flow-derived and lacks verified packet-level features.
- The four capture days provide limited temporal/scenario diversity.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_comparison(path: Path, baseline_path: Path, lstm_metrics: dict[str, Any]) -> None:
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    base = baseline["final_test_metrics"]
    lstm = lstm_metrics["test_metrics"]
    rows = []
    for metric in ("precision", "recall", "f1", "pr_auc", "roc_auc", "false_positive_rate"):
        rows.append(f"| {metric} | {base[metric]:.6f} | {lstm[metric]:.6f} |")
    improvement = lstm["f1"] > base["f1"] and lstm["pr_auc"] > base["pr_auc"]
    content = f"""# Logistic Regression vs LSTM-V1

Both models use the same frozen V1 day-aware test partition. Logistic Regression uses the approved 17 features from one state; LSTM-V1 uses sequences of 10 states and the same pre-aligned target. The LSTM threshold was selected on validation only.

| Metric | Logistic Regression | LSTM-V1 |
|---|---:|---:|
{chr(10).join(rows)}

## Interpretation

Measured LSTM improvement across both F1 and PR-AUC: **{improvement}**.

This is a benchmark comparison, not deployment evidence. A difference can reflect the day/scenario distribution shift between validation and test. No test metric was used for checkpoint or threshold selection.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def train_world_model(
    input_path: Path = DEFAULT_INPUT,
    schema_path: Path = DEFAULT_SCHEMA,
    split_dir: Path = DEFAULT_SPLIT_DIR,
    split_report_path: Path = DEFAULT_SPLIT_REPORT,
    checkpoint_path: Path = DEFAULT_CHECKPOINT,
    config_path: Path = DEFAULT_CONFIG,
    metrics_path: Path = DEFAULT_METRICS,
    metadata_path: Path = DEFAULT_METADATA,
    report_path: Path = DEFAULT_REPORT,
    comparison_path: Path = DEFAULT_COMPARISON,
    baseline_results_path: Path = PROJECT_ROOT / "results" / "BASELINE_TEST_RESULTS.json",
) -> dict[str, Any]:
    if not input_path.is_file() or not split_report_path.is_file():
        raise FileNotFoundError("Frozen V1 input or approved split report is missing")
    feature_columns, schema_version = _load_features(schema_path)
    split_report = json.loads(split_report_path.read_text(encoding="utf-8"))
    if split_report.get("split_day_overlap") is not False:
        raise ValueError("Approved split report does not prove day disjointness")
    frames = {name: _load_split(split_dir / f"{name}.parquet", feature_columns) for name in ("train", "validation", "test")}
    preprocessor = BaselinePreprocessor(feature_columns)
    train_transformed = _transform_split(frames["train"], preprocessor.fit(frames["train"]), feature_columns)
    validation_transformed = _transform_split(frames["validation"], preprocessor, feature_columns)
    test_transformed = _transform_split(frames["test"], preprocessor, feature_columns)
    sequence_length = 10
    forecast_horizon = 1
    train_batch = build_sequences(train_transformed, feature_columns, "future_attack_state", sequence_length, forecast_horizon)
    validation_batch = build_sequences(validation_transformed, feature_columns, "future_attack_state", sequence_length, forecast_horizon)
    test_batch = build_sequences(test_transformed, feature_columns, "future_attack_state", sequence_length, forecast_horizon)
    for name, batch in (("train", train_batch), ("validation", validation_batch), ("test", test_batch)):
        if batch.features.shape[2] != 17 or not np.isfinite(batch.features).all():
            raise ValueError(f"Invalid {name} sequence tensor")

    positive = int((train_batch.targets == 1).sum())
    negative = int((train_batch.targets == 0).sum())
    if positive == 0:
        raise ValueError("Training sequences contain no positive target")
    positive_weight = negative / positive
    if not np.isfinite(positive_weight) or positive_weight <= 0:
        raise ValueError("Training-derived positive class weight is invalid")

    config = LSTMConfig(
        input_size=17,
        hidden_size=64,
        num_layers=1,
        dropout=0.0,
        learning_rate=1e-3,
        batch_size=128,
        epochs=20,
        sequence_length=sequence_length,
        forecast_horizon=forecast_horizon,
        random_seed=42,
        device="cpu",
    )
    weighted_run = _train_variant(train_batch, validation_batch, config, positive_weight, weighted=True)
    unweighted_run = _train_variant(train_batch, validation_batch, config, positive_weight, weighted=False)
    validation_probability = weighted_run["best_validation_probabilities"]
    threshold_rows = threshold_table(validation_batch.targets, validation_probability, THRESHOLDS)
    selected_row = select_threshold_by_validation(threshold_rows)
    selected_threshold = float(selected_row["threshold"])
    validation_metrics = evaluate_binary(validation_batch.targets, validation_probability, selected_threshold)
    weighted_model = weighted_run["model"]
    weighted_model.eval()
    with torch.no_grad():
        test_logits = weighted_model(torch.from_numpy(test_batch.features.astype("float32")))
        test_probability = torch.sigmoid(test_logits).numpy()
    test_metrics = evaluate_binary(test_batch.targets, test_probability, selected_threshold)
    if not np.isfinite(test_probability).all() or ((test_probability < 0) | (test_probability > 1)).any():
        raise ValueError("LSTM produced invalid test probabilities")

    training_metadata = {
        "loss_variant": "training_weighted_bce",
        "positive_weight": positive_weight,
        "best_epoch": weighted_run["best_epoch"],
        "best_validation_metric": weighted_run["best_validation_metric"],
        "threshold_selection_split": "validation",
        "test_evaluated_once_after_selection": True,
    }
    save_checkpoint(
        checkpoint_path,
        weighted_model,
        feature_columns,
        "future_attack_state",
        "docs/TARGET_STATE_SPEC.md",
        schema_version,
        selected_threshold,
        weighted_run["best_epoch"],
        weighted_run["best_validation_metric"],
        training_metadata,
    )
    config_document = {
        **config.to_dict(),
        "feature_columns": feature_columns,
        "target_column": "future_attack_state",
        "target_version": "docs/TARGET_STATE_SPEC.md",
        "feature_schema_version": schema_version,
        "loss": "BCEWithLogitsLoss(pos_weight=training_negative_count/training_positive_count)",
        "positive_weight": positive_weight,
        "selected_threshold": selected_threshold,
        "best_epoch": weighted_run["best_epoch"],
    }
    _write_json(config_path, config_document)
    sample_counts = {
        name: {
            "sequences": int(len(batch.targets)),
            "positive": int((batch.targets == 1).sum()),
            "negative": int((batch.targets == 0).sum()),
            "input_shape": list(batch.features.shape),
            "target_shape": list(batch.targets.shape),
        }
        for name, batch in (("train", train_batch), ("validation", validation_batch), ("test", test_batch))
    }
    result: dict[str, Any] = {
        "experiment": "LSTM-V1",
        "input_path": str(input_path.resolve()),
        "schema_version": schema_version,
        "config": config_document,
        "positive_weight": positive_weight,
        "best_epoch": weighted_run["best_epoch"],
        "best_validation_loss": weighted_run["best_validation_loss"],
        "sample_counts": sample_counts,
        "selected_threshold": selected_threshold,
        "validation_metrics": validation_metrics,
        "test_metrics": test_metrics,
        "loss_variant_comparison": {
            "unweighted": {
                "best_epoch": unweighted_run["best_epoch"],
                "validation_pr_auc": unweighted_run["best_validation_metrics_at_0_5"]["pr_auc"],
                "validation_f1": unweighted_run["best_validation_metrics_at_0_5"]["f1"],
            },
            "weighted": {
                "best_epoch": weighted_run["best_epoch"],
                "validation_pr_auc": weighted_run["best_validation_metrics_at_0_5"]["pr_auc"],
                "validation_f1": weighted_run["best_validation_metrics_at_0_5"]["f1"],
            },
        },
        "threshold_rows": threshold_rows,
        "training_history": weighted_run["history"],
        "artifacts": {
            "checkpoint": str(checkpoint_path.resolve()),
            "config": str(config_path.resolve()),
            "metrics": str(metrics_path.resolve()),
            "metadata": str(metadata_path.resolve()),
        },
    }
    _write_json(metrics_path, result)
    metadata = {
        "experiment": "LSTM-V1",
        "dataset_version": "network-state-v1.0",
        "dataset_path": result["input_path"],
        "feature_schema_version": schema_version,
        "target_version": "docs/TARGET_STATE_SPEC.md",
        "feature_count": 17,
        "target_column": "future_attack_state",
        "configuration": config_document,
        "positive_weight": positive_weight,
        "sample_counts": sample_counts,
        "best_epoch": weighted_run["best_epoch"],
        "selected_threshold": selected_threshold,
        "threshold_selection_split": "validation",
        "test_used_for_selection": False,
        "device": "cpu",
        "python_version": platform.python_version(),
        "library_versions": {package: version(package) for package in ("numpy", "pandas", "pyarrow", "scikit-learn", "PyYAML", "joblib", "torch")},
        "artifacts": result["artifacts"],
    }
    _write_json(metadata_path, metadata)
    _write_lstm_report(report_path, result, json.loads(baseline_results_path.read_text(encoding="utf-8")))
    _write_comparison(comparison_path, baseline_results_path, result)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--split-dir", type=Path, default=DEFAULT_SPLIT_DIR)
    parser.add_argument("--split-report", type=Path, default=DEFAULT_SPLIT_REPORT)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--metrics", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--comparison", type=Path, default=DEFAULT_COMPARISON)
    parser.add_argument("--baseline-results", type=Path, default=PROJECT_ROOT / "results" / "BASELINE_TEST_RESULTS.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = train_world_model(
            input_path=args.input,
            schema_path=args.schema,
            split_dir=args.split_dir,
            split_report_path=args.split_report,
            checkpoint_path=args.checkpoint,
            config_path=args.config,
            metrics_path=args.metrics,
            metadata_path=args.metadata,
            report_path=args.report,
            comparison_path=args.comparison,
            baseline_results_path=args.baseline_results,
        )
    except (FileNotFoundError, ValueError, TypeError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    test = result["test_metrics"]
    print(f"Best epoch={result['best_epoch']} threshold={result['selected_threshold']:.2f} positive_weight={result['positive_weight']:.6f}")
    print(f"Test precision={test['precision']:.6f} recall={test['recall']:.6f} F1={test['f1']:.6f}")
    print(f"Test PR-AUC={test['pr_auc']:.6f} ROC-AUC={test['roc_auc']:.6f} FPR={test['false_positive_rate']:.6f}")
    print(f"Checkpoint: {args.checkpoint.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
