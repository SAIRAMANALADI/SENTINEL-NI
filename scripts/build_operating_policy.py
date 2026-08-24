"""Build the validation-only operating threshold and mode policy."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.operating_policy import compute_threshold_sweep  # noqa: E402
from src.forecasting.windowing import build_multistep_sequences  # noqa: E402
from src.models.baseline_preprocessing import BaselinePreprocessor  # noqa: E402
from src.models.lstm_world_model import load_checkpoint  # noqa: E402


FEATURE_SCHEMA = PROJECT_ROOT / "configs" / "state_feature_schema.yaml"
TRAIN_SPLIT = PROJECT_ROOT / "data" / "processed" / "states" / "train.parquet"
VALIDATION_SPLIT = PROJECT_ROOT / "data" / "processed" / "states" / "validation.parquet"
CHECKPOINT = PROJECT_ROOT / "models" / "lstm_multistep_k5.pt"
SWEEP_CSV = PROJECT_ROOT / "results" / "THRESHOLD_POLICY_SWEEP.csv"
SWEEP_REPORT = PROJECT_ROOT / "results" / "THRESHOLD_POLICY_SWEEP.md"
MODES_REPORT = PROJECT_ROOT / "results" / "OPERATING_MODES.md"
POLICY_CONFIG = PROJECT_ROOT / "configs" / "operating_policy.yaml"
FINAL_REPORT = PROJECT_ROOT / "results" / "OPERATING_POLICY_FINAL.md"

SEQUENCE_LENGTH = 10
HORIZON = 5
FORECAST_OFFSET_SECONDS = 10
THRESHOLDS = tuple(round(value, 2) for value in np.arange(0.05, 0.951, 0.01))


def _feature_columns() -> list[str]:
    schema = yaml.safe_load(FEATURE_SCHEMA.read_text(encoding="utf-8"))
    columns = schema.get("FEATURE_COLUMNS")
    if not isinstance(columns, list) or len(columns) != 17:
        raise ValueError("the frozen feature schema must define exactly 17 features")
    return [str(column) for column in columns]


def _transform(frame: pd.DataFrame, preprocessor: BaselinePreprocessor, columns: list[str]) -> pd.DataFrame:
    transformed = preprocessor.transform(frame).reset_index(drop=True)
    metadata = frame.drop(columns=columns).reset_index(drop=True)
    return pd.concat([metadata, transformed], axis=1)


def _validation_scores() -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    columns = _feature_columns()
    train = pd.read_parquet(TRAIN_SPLIT)
    validation = pd.read_parquet(VALIDATION_SPLIT)
    required = set(columns) | {"binary_attack_state", "timestamp", "capture_day"}
    for path, frame in ((TRAIN_SPLIT, train), (VALIDATION_SPLIT, validation)):
        missing = sorted(required - set(frame.columns))
        if missing:
            raise ValueError(f"{path} is missing required columns: {missing}")
    preprocessor = BaselinePreprocessor(columns)
    preprocessor.fit(train)
    transformed = _transform(validation, preprocessor, columns)
    batch = build_multistep_sequences(
        transformed,
        columns,
        "binary_attack_state",
        sequence_length=SEQUENCE_LENGTH,
        forecast_horizon=HORIZON,
    )
    model, checkpoint = load_checkpoint(CHECKPOINT, device="cpu")
    with torch.no_grad():
        logits = model(torch.from_numpy(batch.features.astype("float32")))
        scores = torch.sigmoid(logits).cpu().numpy()
    scores = scores[:, 0]
    labels = batch.targets[:, 0].astype("int8")
    if not np.isfinite(scores).all():
        raise ValueError("validation scores contain non-finite values")
    metadata = {
        "validation_sequences": int(len(labels)),
        "positive_support": int(labels.sum()),
        "negative_support": int((labels == 0).sum()),
        "checkpoint": str(CHECKPOINT.relative_to(PROJECT_ROOT)),
        "checkpoint_selected_threshold": checkpoint.get("selected_threshold"),
    }
    return labels, scores, metadata


def _select_modes(rows: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    # These constraints are declared before reading any test artifact. They
    # encode operational intent rather than selecting the largest F1 alone.
    sensitive_candidates = [row for row in rows if row["false_positive_rate"] <= 0.25]
    sensitive = max(sensitive_candidates, key=lambda row: (row["recall"], -row["threshold"]))

    balanced_candidates = [
        row for row in rows
        if row["false_positive_rate"] <= 0.10 and row["recall"] > 0.0
    ]
    if not balanced_candidates:
        balanced_candidates = [row for row in rows if row["recall"] > 0.0]
    balanced = min(
        balanced_candidates,
        key=lambda row: (abs(row["precision"] - row["recall"]), -row["precision"], row["threshold"]),
    )

    conservative_candidates = [row for row in rows if row["recall"] > 0.0]
    conservative = min(
        conservative_candidates,
        key=lambda row: (row["false_positive_rate"], -row["precision"], -row["threshold"]),
    )
    return {"sensitive": sensitive, "balanced": balanced, "conservative": conservative}


def _write_policy(rows: list[dict[str, object]], modes: dict[str, dict[str, object]], metadata: dict[str, object]) -> None:
    SWEEP_CSV.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows)
    frame.to_csv(SWEEP_CSV, index=False, float_format="%.12f")
    selected = {
        name: {
            "threshold": float(row["threshold"]),
            "precision": float(row["precision"]),
            "recall": float(row["recall"]),
            "f1": float(row["f1"]),
            "false_positive_rate": float(row["false_positive_rate"]),
            "alert_count": int(row["alert_count"]),
            "alerts_per_minute": float(row["alerts_per_minute"]),
            "selection_rule": {
                "sensitive": "maximum validation recall subject to validation FPR <= 0.25",
                "balanced": "minimum absolute precision-recall gap subject to validation FPR <= 0.10 and recall > 0; fallback recall > 0",
                "conservative": "minimum validation FPR subject to recall > 0",
            }[name],
        }
        for name, row in modes.items()
    }
    report_lines = [
        "# Threshold Policy Sweep",
        "",
        "The frozen K=5 direct model's first output (+10 seconds) was scored on the validation split only. Thresholds run from 0.05 to 0.95 inclusive in 0.01 increments.",
        "",
        f"- Validation sequences: {metadata['validation_sequences']:,}",
        f"- Positive support: {metadata['positive_support']:,}",
        f"- Negative support: {metadata['negative_support']:,}",
        f"- Checkpoint: `{metadata['checkpoint']}`",
        "- Final test data was not loaded or used for threshold/mode selection.",
        "- Alerts per minute is a state-rate estimate assuming one 10-second state per interval.",
        "",
        "## Selected validation operating points",
        "",
        "| Mode | Threshold | Precision | Recall | F1 | FPR | Alerts | Alerts/min | Rule |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for name in ("sensitive", "balanced", "conservative"):
        item = selected[name]
        report_lines.append(
            f"| {name} | {item['threshold']:.2f} | {item['precision']:.6f} | {item['recall']:.6f} | {item['f1']:.6f} | {item['false_positive_rate']:.6f} | {item['alert_count']:,} | {item['alerts_per_minute']:.3f} | {item['selection_rule']} |"
        )
    report_lines.extend(["", "The complete machine-readable sweep is in `results/THRESHOLD_POLICY_SWEEP.csv`.", ""])
    SWEEP_REPORT.write_text("\n".join(report_lines), encoding="utf-8")

    modes_lines = [
        "# Operating Modes",
        "",
        "All modes use the same frozen K=5 model and the +10-second output. Only the decision threshold changes. Thresholds were selected from validation data under predeclared rules; the final test day was not used.",
        "",
        "| Mode | Threshold | Intended use | Validation evidence |",
        "|---|---:|---|---|",
    ]
    intended = {
        "sensitive": "Exploratory monitoring where missed warnings are costly; expect more false alerts.",
        "balanced": "Primary demo mode; moderate alerting with an explicit validation FPR constraint.",
        "conservative": "High-confidence triage; accepts missed positives to reduce false alerts.",
    }
    for name in ("sensitive", "balanced", "conservative"):
        item = selected[name]
        modes_lines.append(
            f"| {name} | {item['threshold']:.2f} | {intended[name]} | precision {item['precision']:.6f}, recall {item['recall']:.6f}, FPR {item['false_positive_rate']:.6f}, alerts/min {item['alerts_per_minute']:.3f} |"
        )
    modes_lines.extend([
        "",
        "No mode is a universally best operating point. The balanced mode is the primary demo choice because it is the least misleading default for a demo, while sensitive and conservative modes expose the alerting trade-off explicitly.",
        "",
        "The scores remain model scores, not validated probabilities; see `docs/CALIBRATION_POLICY.md`.",
    ])
    MODES_REPORT.write_text("\n".join(modes_lines) + "\n", encoding="utf-8")

    policy = {
        "policy_version": "operating-policy-v1",
        "dataset_version": "network-state-v1.0",
        "selection_split": "validation",
        "test_used_for_selection": False,
        "checkpoint": metadata["checkpoint"],
        "forecast_horizon": 1,
        "forecast_offset_seconds": FORECAST_OFFSET_SECONDS,
        "sequence_length": SEQUENCE_LENGTH,
        "score_name": "Forecast Score",
        "warning_label": "Predictive warning",
        "no_warning_label": "No predictive warning",
        "primary_mode": "balanced",
        "modes": {
            name: {
                "threshold": float(selected[name]["threshold"]),
                "selection_rule": selected[name]["selection_rule"],
                "validation_metrics": {
                    key: selected[name][key]
                    for key in ("precision", "recall", "f1", "false_positive_rate", "alert_count", "alerts_per_minute")
                },
            }
            for name in ("sensitive", "balanced", "conservative")
        },
        "calibration": {
            "status": "not_calibrated",
            "raw_scores_are_probabilities": False,
            "approved_display_term": "Forecast Score",
        },
    }
    POLICY_CONFIG.write_text(yaml.safe_dump(policy, sort_keys=False), encoding="utf-8")
    FINAL_REPORT.write_text(
        "\n".join([
            "# Operating Policy Final",
            "",
            "Status: **READY FOR DEMO POLICY**",
            "",
            "## Primary forecast",
            "",
            "The primary demo forecast is the K=5 development checkpoint's first output: +10 seconds. K=5 is used because it is the existing controlled multi-step checkpoint and the first output preserves the approved one-step target semantics. This is a demo operating choice, not a claim that K=5 is the final architecture winner.",
            "",
            "## Primary mode",
            "",
            f"- Mode: **balanced**",
            f"- Threshold: **{selected['balanced']['threshold']:.2f}**",
            f"- Validation precision / recall / F1: {selected['balanced']['precision']:.6f} / {selected['balanced']['recall']:.6f} / {selected['balanced']['f1']:.6f}",
            f"- Validation FPR: {selected['balanced']['false_positive_rate']:.6f}",
            f"- Estimated alerts per minute: {selected['balanced']['alerts_per_minute']:.3f}",
            "",
            "## Mode thresholds",
            "",
            *[f"- {name}: {selected[name]['threshold']:.2f}" for name in ("sensitive", "balanced", "conservative")],
            "",
            "## UI semantics",
            "",
            "Display the raw score as **Forecast Score**. At or above the selected threshold display **Predictive warning**; below it display **No predictive warning**. The warning means elevated predicted probability/score of an attack state at +10 seconds; it does not mean an attack was detected or attributed.",
            "",
            "## Calibration",
            "",
            "Raw model scores are not presented as calibrated probabilities. No Platt, isotonic, temperature, or other calibration transform is applied in V1. A future calibration fit must use training/validation data only and must be frozen before any final-test evaluation.",
            "",
            "## Guardrails",
            "",
            "- Selection used validation data only; the final test day was not loaded by this policy-generation script.",
            "- No data, split, model checkpoint, target, or feature pipeline was changed.",
            "- Alert-rate figures are state-rate estimates, not incident counts or continuous-time guarantees.",
            "- The current validation score separation is weak; mode choice should be revisited only with a new approved validation experiment, never by tuning on the frozen test day.",
        ]) + "\n",
        encoding="utf-8",
    )
    return policy


def build_policy() -> dict[str, object]:
    labels, scores, metadata = _validation_scores()
    rows = compute_threshold_sweep(labels, scores, THRESHOLDS, interval_seconds=10)
    modes = _select_modes(rows)
    return _write_policy(rows, modes, metadata)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    return parser.parse_args()


def main() -> int:
    parse_args()
    try:
        policy = build_policy()
    except (FileNotFoundError, ValueError, TypeError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Primary mode: {policy['primary_mode']}")
    for name, mode in policy["modes"].items():
        print(f"{name}: threshold={mode['threshold']:.2f}")
    print(f"Sweep: {SWEEP_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
