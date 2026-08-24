"""Train the Logistic Regression baseline for the frozen V1 state contract."""

from __future__ import annotations

import argparse
import json
import platform
import sys
from importlib.metadata import version
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.baseline_metrics import evaluate_binary, select_threshold_by_validation, threshold_table
from src.models.baseline_preprocessing import BaselinePreprocessor
from src.models.logistic_baseline import LogisticBaseline


DEFAULT_INPUT = PROJECT_ROOT / "data" / "processed" / "cic_ids2018_network_states.parquet"
DEFAULT_SCHEMA = PROJECT_ROOT / "configs" / "state_feature_schema.yaml"
DEFAULT_SPLIT_REPORT = PROJECT_ROOT / "results" / "network_state_split_report.json"
DEFAULT_SPLIT_DIR = PROJECT_ROOT / "data" / "processed" / "states"
DEFAULT_MODEL = PROJECT_ROOT / "models" / "logistic_baseline.joblib"
DEFAULT_PREPROCESSOR = PROJECT_ROOT / "models" / "baseline_preprocessor.joblib"
DEFAULT_TEST_RESULTS = PROJECT_ROOT / "results" / "BASELINE_TEST_RESULTS.json"
DEFAULT_REPORT = PROJECT_ROOT / "results" / "BASELINE_REPORT.md"
DEFAULT_THRESHOLD_REPORT = PROJECT_ROOT / "results" / "BASELINE_THRESHOLD_ANALYSIS.md"
DEFAULT_METADATA = PROJECT_ROOT / "results" / "baseline_run_metadata.json"
THRESHOLDS = (0.30, 0.40, 0.50, 0.60, 0.70)
EXPECTED_DAYS = {
    "train": ["2018-02-14", "2018-02-21"],
    "validation": ["2018-02-22"],
    "test": ["2018-02-28"],
}


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _load_feature_contract(schema_path: Path) -> tuple[list[str], list[str], str]:
    document = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    features = list(document.get("FEATURE_COLUMNS", []))
    targets = list(document.get("TARGET_COLUMNS", []))
    schema_version = str(document.get("schema_version", ""))
    if len(features) != 17:
        raise ValueError(f"Expected 17 frozen features, found {len(features)}")
    if "future_attack_state" not in targets:
        raise ValueError("Frozen target future_attack_state is absent from the schema")
    if set(features) & set(targets):
        raise ValueError("Target column is included in the frozen feature list")
    return features, targets, schema_version


def _load_split(path: Path, feature_columns: list[str], target_column: str) -> tuple[pd.DataFrame, np.ndarray, dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"Split file does not exist: {path}")
    frame = pd.read_parquet(path)
    required = set(feature_columns) | {target_column, "future_target_available", "capture_day", "timestamp"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{path} is missing required columns: {missing}")
    observed_days = sorted(frame["capture_day"].astype(str).unique().tolist())
    split_name = path.stem
    if observed_days != EXPECTED_DAYS[split_name]:
        raise ValueError(f"{split_name} contains unexpected capture days: {observed_days}")
    usable = frame.loc[frame["future_target_available"].astype(bool)].copy()
    target = usable[target_column].to_numpy(dtype="int8")
    if set(np.unique(target)) - {0, 1}:
        raise ValueError(f"{split_name} target contains values outside {{0, 1}}")
    values = usable[feature_columns].to_numpy(dtype="float64")
    if not np.isfinite(values).all():
        raise ValueError(f"{split_name} contains non-finite model features")
    distribution = {
        "states": int(len(frame)),
        "usable_supervised_states": int(len(usable)),
        "positive": int((target == 1).sum()),
        "negative": int((target == 0).sum()),
        "capture_days": observed_days,
    }
    return usable, target, distribution


def _library_versions() -> dict[str, str]:
    packages = ("numpy", "pandas", "pyarrow", "scikit-learn", "PyYAML", "joblib")
    return {package: version(package) for package in packages}


def _choose_class_weight(validation_results: dict[str | None, dict[str, Any]]) -> str | None:
    ranked = sorted(
        validation_results.items(),
        key=lambda item: (
            -(item[1]["pr_auc"] if item[1]["pr_auc"] is not None else -1.0),
            -item[1]["f1"],
            0 if item[0] is None else 1,
        ),
    )
    return ranked[0][0]


def _write_threshold_report(path: Path, rows: list[dict[str, Any]], selected: dict[str, Any], class_weight: str | None) -> None:
    lines = [
        "# Baseline Threshold Analysis",
        "",
        "Threshold selection used validation data only. The test set was not inspected during threshold selection.",
        "",
        f"Selected model class weight: `{class_weight}`",
        f"Selected threshold: **{selected['threshold']:.2f}**",
        "",
        "| Threshold | Precision | Recall | F1 | FPR | PR-AUC |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        marker = " **selected**" if row["threshold"] == selected["threshold"] else ""
        pr_auc = "NA" if row["pr_auc"] is None else f"{row['pr_auc']:.6f}"
        fpr = "NA" if row["false_positive_rate"] is None else f"{row['false_positive_rate']:.6f}"
        lines.append(
            f"| {row['threshold']:.2f}{marker} | {row['precision']:.6f} | {row['recall']:.6f} | "
            f"{row['f1']:.6f} | {fpr} | {pr_auc} |"
        )
    lines.extend(
        [
            "",
            "Selection rule: highest validation F1, then highest validation recall, then lowest threshold. No test metric was used.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_baseline_report(path: Path, result: dict[str, Any]) -> None:
    validation = result["validation_metrics"]
    test = result["test_metrics"]
    candidate_rows = []
    for name, metrics in result["class_weight_comparison"].items():
        candidate_rows.append(
            f"| `{name}` | {metrics['pr_auc']:.6f} | {metrics['f1']:.6f} | {metrics['precision']:.6f} | {metrics['recall']:.6f} |"
        )
    content = f"""# Logistic Regression Baseline Report

## Dataset

- Input: `{result['input_path']}`
- Schema: `{result['schema_path']}` (`{result['schema_version']}`)
- Features: `{result['feature_count']}` approved V1 state features
- Target: `future_attack_state`
- State interval: 10 seconds

## Samples and split

| Split | States | Usable supervised | Negative | Positive | Capture days |
|---|---:|---:|---:|---:|---|
| Train | {result['class_distribution']['train']['states']:,} | {result['class_distribution']['train']['usable_supervised_states']:,} | {result['class_distribution']['train']['negative']:,} | {result['class_distribution']['train']['positive']:,} | {', '.join(result['class_distribution']['train']['capture_days'])} |
| Validation | {result['class_distribution']['validation']['states']:,} | {result['class_distribution']['validation']['usable_supervised_states']:,} | {result['class_distribution']['validation']['negative']:,} | {result['class_distribution']['validation']['positive']:,} | {', '.join(result['class_distribution']['validation']['capture_days'])} |
| Test | {result['class_distribution']['test']['states']:,} | {result['class_distribution']['test']['usable_supervised_states']:,} | {result['class_distribution']['test']['negative']:,} | {result['class_distribution']['test']['positive']:,} | {', '.join(result['class_distribution']['test']['capture_days'])} |

## Preprocessing

`StandardScaler` was fitted only on the training feature matrix and then reused unchanged for validation and test. The fitted artifact preserves the exact 17 feature names. Non-finite values are rejected rather than imputed.

## Model and selection

- Model: `sklearn.linear_model.LogisticRegression`
- Solver: `liblinear`
- C: `{result['model']['C']}`
- max_iter: `{result['model']['max_iter']}`
- random_state: `{result['model']['random_state']}`
- selected class weight: `{result['model']['class_weight']}`
- selected threshold: `{result['selected_threshold']:.2f}`

Class-weight comparison used validation only:

| Class weight | Validation PR-AUC | Validation F1 @ 0.50 | Precision @ 0.50 | Recall @ 0.50 |
|---|---:|---:|---:|---:|
{chr(10).join(candidate_rows)}

Threshold selection used validation F1, then recall, then lowest threshold. The held-out test set was evaluated once after this selection.

## Metrics

| Metric | Validation at selected threshold | Final test at selected threshold |
|---|---:|---:|
| Precision | {validation['precision']:.6f} | {test['precision']:.6f} |
| Recall | {validation['recall']:.6f} | {test['recall']:.6f} |
| F1 | {validation['f1']:.6f} | {test['f1']:.6f} |
| PR-AUC | {validation['pr_auc']:.6f} | {test['pr_auc']:.6f} |
| ROC-AUC | {validation['roc_auc']:.6f} | {test['roc_auc']:.6f} |
| False-positive rate | {validation['false_positive_rate']:.6f} | {test['false_positive_rate']:.6f} |
| Brier score | {validation['brier_score']:.6f} | {test['brier_score']:.6f} |

- Validation confusion matrix `[ [TN, FP], [FN, TP] ]`: `{validation['confusion_matrix']}`
- Test confusion matrix `[ [TN, FP], [FN, TP] ]`: `{test['confusion_matrix']}`

## Artifacts

- Model: `{result['artifacts']['model']}`
- Preprocessor: `{result['artifacts']['preprocessor']}`
- Test results: `{result['artifacts']['test_results']}`
- Run metadata: `{result['artifacts']['metadata']}`

## Limitations

- This is a Logistic Regression baseline, not a temporal world model.
- The baseline uses one 10-second state at time `t` to predict the already-approved `future_attack_state(t)`; it does not consume temporal sequences.
- The target is observed malicious-traffic presence, not compromise or an entire attack chain.
- The state representation is flow-derived; packet-only requirements remain unavailable.
- Generalization is limited to the four capture days and their documented class distributions.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def train_baseline(
    input_path: Path = DEFAULT_INPUT,
    schema_path: Path = DEFAULT_SCHEMA,
    split_report_path: Path = DEFAULT_SPLIT_REPORT,
    split_dir: Path = DEFAULT_SPLIT_DIR,
    model_path: Path = DEFAULT_MODEL,
    preprocessor_path: Path = DEFAULT_PREPROCESSOR,
    test_results_path: Path = DEFAULT_TEST_RESULTS,
    report_path: Path = DEFAULT_REPORT,
    threshold_report_path: Path = DEFAULT_THRESHOLD_REPORT,
    metadata_path: Path = DEFAULT_METADATA,
) -> dict[str, Any]:
    if not input_path.is_file():
        raise FileNotFoundError(f"Frozen V1 dataset does not exist: {input_path}")
    feature_columns, _target_columns, schema_version = _load_feature_contract(schema_path)
    if not split_report_path.is_file():
        raise FileNotFoundError(f"Approved split report does not exist: {split_report_path}")
    split_report = json.loads(split_report_path.read_text(encoding="utf-8"))
    if split_report.get("split_day_overlap") is not False:
        raise ValueError("Approved split report does not prove day disjointness")

    split_frames: dict[str, pd.DataFrame] = {}
    targets: dict[str, np.ndarray] = {}
    class_distribution: dict[str, dict[str, Any]] = {}
    for split_name in ("train", "validation", "test"):
        frame, target, distribution = _load_split(split_dir / f"{split_name}.parquet", feature_columns, "future_attack_state")
        split_frames[split_name] = frame
        targets[split_name] = target
        class_distribution[split_name] = distribution

    preprocessor = BaselinePreprocessor(feature_columns)
    train_x = preprocessor.fit_transform(split_frames["train"])
    validation_x = preprocessor.transform(split_frames["validation"])
    test_x = preprocessor.transform(split_frames["test"])

    validation_candidates: dict[str | None, dict[str, Any]] = {}
    fitted_models: dict[str | None, LogisticBaseline] = {}
    for class_weight in (None, "balanced"):
        model = LogisticBaseline(
            feature_columns,
            C=1.0,
            max_iter=1000,
            class_weight=class_weight,
            random_state=42,
        )
        model.fit(train_x, targets["train"])
        validation_probability = model.predict_probability(validation_x)
        validation_candidates[class_weight] = evaluate_binary(
            targets["validation"], validation_probability, threshold=0.5
        )
        fitted_models[class_weight] = model

    selected_class_weight = _choose_class_weight(validation_candidates)
    selected_model = fitted_models[selected_class_weight]
    validation_probability = selected_model.predict_probability(validation_x)
    validation_thresholds = threshold_table(targets["validation"], validation_probability, THRESHOLDS)
    selected_threshold_row = select_threshold_by_validation(validation_thresholds)
    selected_threshold = float(selected_threshold_row["threshold"])
    validation_metrics = evaluate_binary(
        targets["validation"], validation_probability, threshold=selected_threshold
    )
    test_probability = selected_model.predict_probability(test_x)
    test_metrics = evaluate_binary(targets["test"], test_probability, threshold=selected_threshold)

    selected_model.save(model_path)
    preprocessor.save(preprocessor_path)
    artifacts = {
        "model": str(model_path.resolve()),
        "preprocessor": str(preprocessor_path.resolve()),
        "test_results": str(test_results_path.resolve()),
        "metadata": str(metadata_path.resolve()),
    }
    result: dict[str, Any] = {
        "dataset": "CSE-CIC-IDS2018 multi-day network states V1",
        "input_path": str(input_path.resolve()),
        "schema_path": str(schema_path.resolve()),
        "schema_version": schema_version,
        "feature_count": len(feature_columns),
        "feature_columns": feature_columns,
        "target": {
            "column": "future_attack_state",
            "definition": "binary_attack_state(t + 10 seconds) within the same capture_day",
            "availability_filter": "future_target_available == true",
        },
        "state_interval_seconds": 10,
        "class_distribution": class_distribution,
        "split_report": split_report,
        "class_weight_comparison": {
            "none": validation_candidates[None],
            "balanced": validation_candidates["balanced"],
        },
        "model": {
            "type": "LogisticRegression",
            "solver": "liblinear",
            "C": 1.0,
            "max_iter": 1000,
            "random_state": 42,
            "class_weight": selected_class_weight,
        },
        "preprocessing": {
            "type": "StandardScaler",
            "fit_split": "train",
            "fit_row_count": preprocessor.fit_row_count,
            "feature_names_preserved": True,
        },
        "selected_threshold": selected_threshold,
        "validation_metrics": validation_metrics,
        "test_metrics": test_metrics,
        "threshold_rows": validation_thresholds,
        "artifacts": artifacts,
    }
    _write_threshold_report(threshold_report_path, validation_thresholds, selected_threshold_row, selected_class_weight)
    _write_baseline_report(report_path, result)
    _write_json(
        test_results_path,
        {
            "dataset": result["dataset"],
            "input_path": result["input_path"],
            "feature_columns": feature_columns,
            "target": result["target"],
            "split_counts": class_distribution,
            "model": result["model"],
            "selected_threshold": selected_threshold,
            "validation_metrics": validation_metrics,
            "final_test_metrics": test_metrics,
            "class_weight_comparison": result["class_weight_comparison"],
            "test_evaluated_once_after_validation_selection": True,
        },
    )
    metadata = {
        "dataset_version": "network-state-v1.0",
        "dataset_path": result["input_path"],
        "feature_schema_version": schema_version,
        "target_version": "docs/TARGET_STATE_SPEC.md",
        "feature_count": len(feature_columns),
        "target_column": "future_attack_state",
        "model_parameters": result["model"],
        "preprocessing_parameters": result["preprocessing"],
        "selected_threshold": selected_threshold,
        "random_seed": 42,
        "library_versions": _library_versions(),
        "python_version": platform.python_version(),
        "threshold_selection_split": "validation",
        "test_used_for_selection": False,
        "artifacts": artifacts,
    }
    _write_json(metadata_path, metadata)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--split-report", type=Path, default=DEFAULT_SPLIT_REPORT)
    parser.add_argument("--split-dir", type=Path, default=DEFAULT_SPLIT_DIR)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--preprocessor", type=Path, default=DEFAULT_PREPROCESSOR)
    parser.add_argument("--test-results", type=Path, default=DEFAULT_TEST_RESULTS)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--threshold-report", type=Path, default=DEFAULT_THRESHOLD_REPORT)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = train_baseline(
            input_path=args.input,
            schema_path=args.schema,
            split_report_path=args.split_report,
            split_dir=args.split_dir,
            model_path=args.model,
            preprocessor_path=args.preprocessor,
            test_results_path=args.test_results,
            report_path=args.report,
            threshold_report_path=args.threshold_report,
            metadata_path=args.metadata,
        )
    except (FileNotFoundError, ValueError, TypeError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    test = result["test_metrics"]
    print(f"Selected class_weight={result['model']['class_weight']!r} threshold={result['selected_threshold']:.2f}")
    print(f"Test precision={test['precision']:.6f} recall={test['recall']:.6f} F1={test['f1']:.6f}")
    print(f"Test PR-AUC={test['pr_auc']:.6f} ROC-AUC={test['roc_auc']:.6f} FPR={test['false_positive_rate']:.6f}")
    print(f"Model: {args.model.resolve()}")
    print(f"Preprocessor: {args.preprocessor.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
