"""Build deterministic K-step row windows without crossing split boundaries."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.forecasting.windowing import generate_temporal_windows
from src.preprocessing.data import load_modeling_frame
from src.preprocessing.split import chronological_split


DEFAULT_INPUT = PROJECT_ROOT / "data" / "processed" / "cic_ids2018_model_features.parquet"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "processed" / "cic_ids2018_temporal_windows.npz"
DEFAULT_REPORT = PROJECT_ROOT / "results" / "window_report.json"
DEFAULT_SPLIT_REPORT = PROJECT_ROOT / "results" / "split_report.json"


def build_windows(
    input_path: Path,
    output_path: Path = DEFAULT_OUTPUT,
    report_path: Path = DEFAULT_REPORT,
    split_report_path: Path = DEFAULT_SPLIT_REPORT,
    sequence_length: int = 5,
    stride: int = 5,
    horizon: int = 1,
) -> dict[str, object]:
    data, feature_columns, _ = load_modeling_frame(input_path)
    split_result = chronological_split(data)
    frame = split_result.frame
    result = generate_temporal_windows(
        frame[feature_columns],
        frame["timestamp_parsed"],
        frame["binary_label"],
        frame["split"],
        sequence_length=sequence_length,
        stride=stride,
        forecast_horizon=horizon,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_path,
        train_features=result.features["train"],
        validation_features=result.features["validation"],
        test_features=result.features["test"],
        train_targets=result.targets["train"],
        validation_targets=result.targets["validation"],
        test_targets=result.targets["test"],
        train_origins=result.origins["train"].astype("int64"),
        validation_origins=result.origins["validation"].astype("int64"),
        test_origins=result.origins["test"].astype("int64"),
        train_target_times=result.target_times["train"].astype("int64"),
        validation_target_times=result.target_times["validation"].astype("int64"),
        test_target_times=result.target_times["test"].astype("int64"),
        train_origin_positions=result.origin_positions["train"],
        validation_origin_positions=result.origin_positions["validation"],
        test_origin_positions=result.origin_positions["test"],
        train_target_positions=result.target_positions["train"],
        validation_target_positions=result.target_positions["validation"],
        test_target_positions=result.target_positions["test"],
    )
    report = {
        **result.report,
        "input_path": str(input_path.resolve()),
        "output_path": str(output_path.resolve()),
        "feature_columns": feature_columns,
        "split_report": split_result.report,
        "window_target": "binary attack state at t+1; Benign=0, Infilteration=1",
        "row_sequence_limitation": "These are flow-row sequences, not fixed-interval network-state aggregates; this is an initial temporal mechanics experiment.",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    split_report_path.parent.mkdir(parents=True, exist_ok=True)
    split_report_path.write_text(json.dumps(split_result.report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--sequence-length", type=int, required=True)
    parser.add_argument("--stride", type=int, default=5)
    parser.add_argument("--horizon", type=int, default=1)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--split-report", type=Path, default=DEFAULT_SPLIT_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = build_windows(
            args.input,
            args.output,
            args.report,
            args.split_report,
            args.sequence_length,
            args.stride,
            args.horizon,
        )
    except (FileNotFoundError, ValueError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Window counts: {report['split_window_counts']}")
    print(f"Feature dimension: {report['feature_dimension']}")
    print(f"Windows: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
