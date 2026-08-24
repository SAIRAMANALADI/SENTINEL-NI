"""Create fixed, capture-day-isolated train/validation/test state files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.features.network_state import FEATURE_COLUMNS, TARGET_COLUMNS, METADATA_COLUMNS

DEFAULT_INPUT = PROJECT_ROOT / "data" / "processed" / "cic_ids2018_network_states.parquet"
DEFAULT_SPLIT_REPORT = PROJECT_ROOT / "results" / "multiday_split_report.json"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "states"
DEFAULT_REPORT = PROJECT_ROOT / "results" / "network_state_split_report.json"


def build_splits(input_path: Path, split_report_path: Path, output_dir: Path, report_path: Path) -> dict[str, object]:
    frame = pd.read_parquet(input_path)
    split = json.loads(split_report_path.read_text(encoding="utf-8"))
    day_roles: dict[str, str] = {}
    for role in ("train", "validation", "test"):
        for day in split[f"{role}_days"]:
            if day in day_roles:
                raise ValueError(f"Capture day assigned to multiple state splits: {day}")
            day_roles[day] = role
    frame["split"] = frame["capture_day"].astype("string").map(day_roles)
    if frame["split"].isna().any():
        raise ValueError("Network-state rows contain an unassigned capture day")
    if frame["future_target_available"].dtype == bool:
        pass
    if frame[FEATURE_COLUMNS].isna().any().any():
        raise ValueError("Network-state features contain missing values")
    if not all(pd.api.types.is_numeric_dtype(frame[column]) for column in FEATURE_COLUMNS):
        raise ValueError("Network-state feature schema contains non-numeric columns")
    if not np.isfinite(frame[FEATURE_COLUMNS].to_numpy(dtype="float64")).all():
        raise ValueError("Network-state features contain non-finite values")
    if frame.duplicated(["capture_day", "timestamp"]).any():
        raise ValueError("Duplicate state timestamps exist within a capture day")
    frame = frame.sort_values(["capture_day", "timestamp"], kind="mergesort").reset_index(drop=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    split_summary: dict[str, object] = {}
    for role in ("train", "validation", "test"):
        part = frame.loc[frame["split"] == role].drop(columns=["split"]).copy()
        if part.empty:
            raise ValueError(f"State split is empty: {role}")
        for day in part["capture_day"].unique():
            day_part = part.loc[part["capture_day"] == day]
            if not day_part["timestamp"].is_monotonic_increasing:
                raise ValueError(f"State timestamps are not chronological: {role}/{day}")
        destination = output_dir / f"{role}.parquet"
        pq.write_table(pa.Table.from_pandas(part, preserve_index=False), destination, compression="snappy")
        target_counts = part.loc[part["future_target_available"], "future_attack_state"].value_counts().to_dict()
        split_summary[role] = {
            "path": str(destination.resolve()),
            "state_count": int(len(part)),
            "capture_days": sorted(part["capture_day"].astype(str).unique().tolist()),
            "timestamp_min": part["timestamp"].min().isoformat(sep=" "),
            "timestamp_max": part["timestamp"].max().isoformat(sep=" "),
            "future_target_available_count": int(part["future_target_available"].sum()),
            "future_target_unavailable_count": int((~part["future_target_available"]).sum()),
            "future_attack_state_counts": {str(key): int(value) for key, value in target_counts.items()},
        }
    report = {
        "schema_version": "network-state-v1.0",
        "input": str(input_path.resolve()),
        "feature_columns": FEATURE_COLUMNS,
        "target_columns": TARGET_COLUMNS,
        "metadata_columns": METADATA_COLUMNS,
        "method": "complete capture-day split from results/multiday_split_report.json; no random row split",
        "anomaly_policy": "14 timestamp/capture-date mismatches excluded before state construction; raw flow records preserved",
        "split_summary": split_summary,
        "split_day_overlap": False,
        "cross_day_aggregation": False,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--split-report", type=Path, default=DEFAULT_SPLIT_REPORT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = build_splits(args.input.resolve(), args.split_report.resolve(), args.output_dir, args.report)
    except (FileNotFoundError, ValueError, TypeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print({role: summary["state_count"] for role, summary in report["split_summary"].items()})
    print(f"Split report: {args.report.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
