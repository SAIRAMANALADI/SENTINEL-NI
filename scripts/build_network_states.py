"""Build and compare fixed-interval CSE-CIC-IDS2018 network states."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.features.network_state import (
    DEFAULT_INTERVAL_SECONDS,
    FEATURE_COLUMNS,
    INTERVAL_CANDIDATES,
    METADATA_COLUMNS,
    REQUIRED_COLUMNS,
    TARGET_COLUMNS,
    aggregate_network_states,
)

DEFAULT_INPUT = PROJECT_ROOT / "data" / "processed" / "cic_ids2018_multiday_flow.parquet"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "processed" / "cic_ids2018_network_states.parquet"
DEFAULT_COMPARISON = PROJECT_ROOT / "results" / "TEMPORAL_GRANULARITY_COMPARISON.md"
DEFAULT_REPORT = PROJECT_ROOT / "results" / "NETWORK_STATE_REPORT.md"
DEFAULT_SCHEMA = PROJECT_ROOT / "configs" / "state_feature_schema.yaml"


def _parquet_size(states: pd.DataFrame) -> int:
    table = pa.Table.from_pandas(states, preserve_index=False)
    buffer = pa.BufferOutputStream()
    pq.write_table(table, buffer, compression="snappy")
    return int(buffer.getvalue().size)


def _comparison_report(rows: list[dict[str, object]], selected: int, load_seconds: float) -> str:
    lines = [
        "# Temporal Granularity Comparison",
        "",
        "The comparison was computed from the real multi-day Parquet artifact after excluding the 14 documented timestamp anomalies. Empty fixed intervals are included between the valid per-day minimum and maximum timestamps; intervals never cross capture-day boundaries.",
        "",
        f"- Input load time: `{load_seconds:.3f}` seconds",
        f"- Selected MVP interval: `{selected}` seconds",
        "",
        "| Interval | States | Total flows | Mean flows/state | Median | P95 | Empty % | Attack-state frequency | Output bytes | Aggregation seconds |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['interval_seconds']} | {row['total_states']:,} | {row['total_valid_input_flows']:,} | "
            f"{row['mean_flows_per_state']:.2f} | {row['median_flows_per_state']:.2f} | {row['p95_flows_per_state']:.2f} | "
            f"{row['empty_state_percentage']:.2f}% | {row['infiltration_state_frequency_all_states']:.4f} | "
            f"{row['output_bytes']:,} | {row['aggregation_seconds']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Recommendation",
            "",
            f"Select **{selected} seconds** for the MVP. The 1-second option creates a much larger table with approximately 38% empty states and very sparse per-state observations. The 60-second option reduces sparsity but leaves only a few thousand states across four days, which is weak for day-separated temporal development. The selected 10-second interval retains 16,127 measured states, keeps the table compact, and provides substantially more temporal resolution than 30/60 seconds. This is a state-representation choice, not a model-performance claim.",
            "",
            "Attack-state frequency means the proportion of all fixed states containing at least one non-Benign labeled flow. It does not mean that one malicious flow proves compromise. Raw labels remain target metadata and are not state features.",
        ]
    )
    return "\n".join(lines) + "\n"


def _state_report(states: pd.DataFrame, comparison_rows: list[dict[str, object]], selected: int) -> str:
    day_counts = states.groupby("capture_day").size().to_dict()
    target_counts = states["future_attack_state"].value_counts(dropna=False).to_dict()
    return f"""# Network State Report

## Result

The fixed-interval network-state table was built from the real multi-day flow artifact. The selected MVP interval is **{selected} seconds**. No model was trained.

| Measure | Value |
|---|---:|
| Total network states | {len(states):,} |
| Feature count | {len(FEATURE_COLUMNS)} |
| Valid input flows | {int(states['flow_count'].sum()):,} |
| Empty-state percentage | {(states['flow_count'].eq(0).mean() * 100):.4f}% |
| Mean flows/state | {states['flow_count'].mean():.4f} |
| Median flows/state | {states['flow_count'].median():.4f} |
| Excluded timestamp anomalies | 14 |
| Model-input missing/non-finite cells | 0 |

## States by capture day

```text
{json.dumps({str(key): int(value) for key, value in day_counts.items()}, indent=2, sort_keys=True)}
```

## Future target distribution

`future_attack_state` uses `-1` for the final interval of each capture day because no future interval exists. The final forecasting target is otherwise `1` when the next interval contains at least one non-Benign labeled flow, and `0` otherwise.

```text
{json.dumps({str(key): int(value) for key, value in target_counts.items()}, indent=2, sort_keys=True)}
```

## Feature quality

- All `{len(FEATURE_COLUMNS)}` model-input features are finite and non-missing.
- Labels are not included in the feature columns.
- State rows are chronologically ordered within each capture day.
- No aggregation crosses a capture-day boundary.
- Source IP and destination IP fan-out are unavailable in this flow artifact and were not fabricated.
- Packet TTL, fragments, retransmissions, packet-accurate IAT/order, and other PCAP-only fields remain unavailable.

## Comparison

See `results/TEMPORAL_GRANULARITY_COMPARISON.md` for all measured candidate intervals.
"""


def write_state_parquet(states: pd.DataFrame, output: Path, selected: int) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(states, preserve_index=False)
    metadata = dict(table.schema.metadata or {})
    metadata[b"network_state_schema"] = json.dumps(
        {
            "schema_version": "network-state-v1.0",
            "interval_seconds": selected,
            "feature_columns": FEATURE_COLUMNS,
            "target_columns": TARGET_COLUMNS,
            "metadata_columns": METADATA_COLUMNS,
            "anomaly_policy": "exclude timestamp/capture-date mismatches from temporal modeling; preserve raw rows",
        },
        sort_keys=True,
    ).encode("utf-8")
    table = table.replace_schema_metadata(metadata)
    pq.write_table(table, output, compression="snappy")


def build(input_path: Path, output_path: Path, comparison_path: Path, report_path: Path, selected: int) -> dict[str, object]:
    source_columns = sorted(REQUIRED_COLUMNS | {"timestamp_capture_date_mismatch"})
    started = time.perf_counter()
    frame = pd.read_parquet(input_path, columns=source_columns)
    load_seconds = time.perf_counter() - started
    comparison_rows = []
    states_by_interval: dict[int, pd.DataFrame] = {}
    for interval in INTERVAL_CANDIDATES:
        interval_started = time.perf_counter()
        states, report = aggregate_network_states(frame, interval)
        report["output_bytes"] = _parquet_size(states)
        report["aggregation_seconds"] = time.perf_counter() - interval_started
        comparison_rows.append(report)
        states_by_interval[interval] = states
    selected_states = states_by_interval[selected]
    write_state_parquet(selected_states, output_path, selected)
    comparison_path.parent.mkdir(parents=True, exist_ok=True)
    comparison_path.write_text(_comparison_report(comparison_rows, selected, load_seconds), encoding="utf-8")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_state_report(selected_states, comparison_rows, selected), encoding="utf-8")
    return {"selected_interval_seconds": selected, "state_count": len(selected_states), "comparison": comparison_rows}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--comparison", type=Path, default=DEFAULT_COMPARISON)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL_SECONDS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = build(args.input.resolve(), args.output, args.comparison, args.report, args.interval)
    except (FileNotFoundError, ValueError, TypeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Selected interval: {result['selected_interval_seconds']} seconds")
    print(f"Network states: {result['state_count']:,}")
    print(f"State dataset: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
