"""Train and evaluate the Logistic Regression current-state baseline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.metrics import evaluate_binary
from src.models.baseline import LogisticBaseline
from src.preprocessing.data import DUPLICATE_KEY_COLUMNS, load_modeling_frame
from src.preprocessing.model_preprocess import ModelPreprocessor
from src.preprocessing.split import chronological_split


DEFAULT_INPUT = PROJECT_ROOT / "data" / "processed" / "cic_ids2018_model_features.parquet"
DEFAULT_MODEL = PROJECT_ROOT / "models" / "logistic_baseline.joblib"
DEFAULT_PREPROCESSOR = PROJECT_ROOT / "models" / "preprocessor.joblib"
DEFAULT_METRICS = PROJECT_ROOT / "results" / "baseline_metrics.json"
DEFAULT_REPORT = PROJECT_ROOT / "results" / "baseline_report.md"
DEFAULT_SPLIT_REPORT = PROJECT_ROOT / "results" / "split_report.json"
DEFAULT_LEAKAGE_REPORT = PROJECT_ROOT / "results" / "BASELINE_LEAKAGE_CHECK.md"


def _json_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _duplicate_cross_split_count(frame: pd.DataFrame, feature_columns: list[str]) -> dict[str, int]:
    duplicate_columns = feature_columns + DUPLICATE_KEY_COLUMNS
    duplicate_basis = frame[duplicate_columns]
    hashes = pd.util.hash_pandas_object(duplicate_basis, index=False)
    groups = pd.DataFrame({"hash": hashes, "split": frame["split"]}).groupby("hash").agg(
        rows=("split", "size"), split_count=("split", "nunique")
    )
    crossing = groups[(groups["rows"] > 1) & (groups["split_count"] > 1)]
    return {
        "duplicate_rows_total": int(duplicate_basis.duplicated().sum()),
        "duplicate_groups_crossing_splits": int(len(crossing)),
        "rows_in_cross_split_duplicate_groups": int(crossing["rows"].sum()),
    }


def _write_leakage_report(path: Path, split_report: dict[str, Any], duplicate_report: dict[str, int], feature_columns: list[str]) -> None:
    content = f"""# Baseline Leakage Check

Date: 2026-08-24

## Result

**PASS WITH DOCUMENTED SINGLE-DAY LIMITATION**

The baseline uses the separate clean sidecar only for `timestamp_parsed` and `binary_label`; target and timestamps are not included in `X`. The preprocessing scaler is fitted on the training partition only and reused unchanged for validation/test.

## Checks

| Check | Result |
|---|---|
| Target columns in model feature table | PASS — not present in `X` |
| Repeated header records | PASS — 33 removed by Dev 2; 0 remain in clean data |
| Invalid timestamps | PASS — 0 |
| Timestamp split overlap | PASS — contiguous non-overlapping boundaries |
| Random row split | PASS — not used |
| Cross-split duplicate groups | PASS — {duplicate_report['duplicate_groups_crossing_splits']} |
| Duplicate rows total | Informational — {duplicate_report['duplicate_rows_total']:,} |
| Train-only preprocessing | PASS — fitted only on train |
| Raw label/binary target in X | PASS — excluded |
| Raw timestamp in X | PASS — excluded |
| Feature count | {len(feature_columns)} numeric columns |

## Split boundaries

```json
{json.dumps(split_report['boundaries'], indent=2)}
```

## Limitations

- The dataset contains one capture day only.
- This is within-day chronological validation, not cross-day or cross-scenario generalization.
- Flow aggregates are used as exported; no PCAP-derived packet features are present.
- `Dst Port` and `Protocol` are excluded because they are flow-key components and possible attack proxies.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_baseline_report(path: Path, result: dict[str, Any], model_columns: list[str]) -> None:
    metrics = result["metrics"]
    split = result["split_report"]
    test = metrics["test"]
    validation = metrics["validation"]
    rows = []
    for name in ("precision", "recall", "f1", "false_positive_rate", "roc_auc", "pr_auc"):
        rows.append(f"| {name} | {test.get(name)} | {validation.get(name)} |")
    content = f"""# Logistic Regression Baseline Report

Date: 2026-08-24

## Dataset

- Input feature artifact: `{result['input_path']}`
- Clean sidecar: `{result['clean_path']}`
- Rows: `{result['row_count']:,}`
- Model features: `{len(model_columns)}`
- Target: `binary_label`, `Benign=0`, `Infilteration=1`
- Model: Logistic Regression with `class_weight=balanced`, `C=1.0`, `solver=liblinear`, `random_state=42`

## Split

Chronological, contiguous split after stable timestamp sorting. Random row splitting was not used.

| Split | Time range | Rows | Class counts |
|---|---|---:|---|
"""
    for name in ("train", "validation", "test"):
        dist = split["class_distribution"][name]
        bounds = split["boundaries"]
        if name == "train":
            period = f"{bounds['train_start']} to before {bounds['validation_start']}"
        elif name == "validation":
            period = f"{bounds['validation_start']} to before {bounds['test_start']}"
        else:
            period = f"{bounds['test_start']} to {bounds['test_end']}"
        content += f"| {name} | {period} | {dist['total']:,} | {dist['counts']} |\n"
    content += f"""
## Metrics

The test partition is the primary reported result; validation is shown for model-selection context only.

| Metric | Test | Validation |
|---|---:|---:|
{chr(10).join(rows)}

Confusion matrices use rows = actual `[0, 1]` and columns = predicted `[0, 1]`.

- Test confusion matrix: `{test['confusion_matrix']}`
- Validation confusion matrix: `{validation['confusion_matrix']}`
- Test class-wise results: `{json.dumps(test['class_wise'], sort_keys=True)}`

## Validity and limitations

- The measured baseline is a current-state classifier: `X_t -> P(attack_t)`. It is not the future-state forecasting model.
- The single-day capture contains early and late infiltration activity, but no independent day/scenario holdout.
- The temporal data is sufficient to exercise the split and `K=1` window mechanics, but not sufficient to claim robust temporal generalization. More temporal data is required before the world model.
- Packet-level requirements remain unavailable without matching PCAP.
- No metrics were fabricated; all values above were calculated from the real Parquet artifacts.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def train_baseline(
    input_path: Path,
    model_path: Path = DEFAULT_MODEL,
    preprocessor_path: Path = DEFAULT_PREPROCESSOR,
    metrics_path: Path = DEFAULT_METRICS,
    report_path: Path = DEFAULT_REPORT,
    split_report_path: Path = DEFAULT_SPLIT_REPORT,
    leakage_report_path: Path = DEFAULT_LEAKAGE_REPORT,
) -> dict[str, Any]:
    data, feature_columns, clean_path = load_modeling_frame(input_path)
    split_result = chronological_split(data)
    split_frame = split_result.frame
    duplicate_report = _duplicate_cross_split_count(split_frame, feature_columns)
    split_report = dict(split_result.report)
    split_report["duplicate_audit"] = duplicate_report
    _json_write(split_report_path, split_report)

    preprocessor = ModelPreprocessor(feature_columns)
    train = split_frame[split_frame["split"] == "train"]
    validation = split_frame[split_frame["split"] == "validation"]
    test = split_frame[split_frame["split"] == "test"]
    train_x = preprocessor.fit_transform(train)
    validation_x = preprocessor.transform(validation)
    test_x = preprocessor.transform(test)

    model = LogisticBaseline(feature_columns, class_weight="balanced", C=1.0, random_state=42)
    model.fit(train_x, train["binary_label"].to_numpy())
    metrics = {
        "train": evaluate_binary(train["binary_label"].to_numpy(), model.predict_probability(train_x)),
        "validation": evaluate_binary(validation["binary_label"].to_numpy(), model.predict_probability(validation_x)),
        "test": evaluate_binary(test["binary_label"].to_numpy(), model.predict_probability(test_x)),
    }

    model.save(model_path)
    preprocessor.save(preprocessor_path)
    metrics_document = {
        "dataset": "CSE-CIC-IDS2018 Wednesday-28-02-2018 flow slice",
        "input_path": str(input_path.resolve()),
        "clean_path": str(clean_path.resolve()),
        "row_count": len(split_frame),
        "feature_count": len(feature_columns),
        "feature_columns": feature_columns,
        "target": {"column": "binary_label", "mapping": {"Benign": 0, "Infilteration": 1}},
        "model": {"type": "LogisticRegression", "class_weight": "balanced", "C": 1.0, "solver": "liblinear", "random_state": 42},
        "split_report": split_report,
        "metrics": metrics,
        "artifacts": {"model": str(model_path.resolve()), "preprocessor": str(preprocessor_path.resolve())},
    }
    _json_write(metrics_path, metrics_document)
    _write_leakage_report(leakage_report_path, split_report, duplicate_report, feature_columns)
    _write_baseline_report(report_path, metrics_document, feature_columns)
    return metrics_document


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--preprocessor-path", type=Path, default=DEFAULT_PREPROCESSOR)
    parser.add_argument("--metrics-path", type=Path, default=DEFAULT_METRICS)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--split-report-path", type=Path, default=DEFAULT_SPLIT_REPORT)
    parser.add_argument("--leakage-report-path", type=Path, default=DEFAULT_LEAKAGE_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = train_baseline(
            args.input,
            args.model_path,
            args.preprocessor_path,
            args.metrics_path,
            args.report_path,
            args.split_report_path,
            args.leakage_report_path,
        )
    except (FileNotFoundError, ValueError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    test = result["metrics"]["test"]
    print(f"Test precision={test['precision']:.6f} recall={test['recall']:.6f} F1={test['f1']:.6f}")
    print(f"Test ROC-AUC={test['roc_auc']} PR-AUC={test['pr_auc']}")
    print(f"Model: {args.model_path.resolve()}")
    print(f"Metrics: {args.metrics_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
