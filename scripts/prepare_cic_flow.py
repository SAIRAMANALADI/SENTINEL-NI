"""Prepare clean and model-safe CSE-CIC-IDS2018 flow artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.features.validation import validate_flow_dataframe
from src.ingestion.cic_ids2018 import load_cic_ids2018_flow


DEFAULT_INPUT = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "cse-cic-ids2018"
    / "flow"
    / "Wednesday-28-02-2018_TrafficForML_CICFlowMeter.csv"
)
DEFAULT_CLEAN_OUTPUT = PROJECT_ROOT / "data" / "processed" / "cic_ids2018_flow_clean.parquet"
DEFAULT_MODEL_OUTPUT = PROJECT_ROOT / "data" / "processed" / "cic_ids2018_model_features.parquet"
DEFAULT_REPORT_OUTPUT = PROJECT_ROOT / "results" / "CIC_IDS2018_CLEANING_REPORT.md"
DEFAULT_EXCLUSIONS = PROJECT_ROOT / "configs" / "model_feature_exclusions.yaml"


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_exclusions(path: Path) -> dict[str, dict[str, str]]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    fields = document.get("fields", []) if isinstance(document, dict) else []
    return {entry["field"]: entry for entry in fields}


def select_model_features(frame: pd.DataFrame, exclusions: dict[str, dict[str, str]]) -> list[str]:
    excluded = set(exclusions)
    columns = [
        column
        for column in frame.columns
        if column not in excluded and pd.api.types.is_numeric_dtype(frame[column])
    ]
    if not columns:
        raise ValueError("No model-safe numeric feature columns remain after exclusions")
    return columns


def _write_parquet(frame: pd.DataFrame, output: Path, metadata: dict[str, Any]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pandas(frame, preserve_index=False)
    existing = dict(table.schema.metadata or {})
    existing[b"cic_ids2018_provenance"] = json.dumps(
        metadata, sort_keys=True, default=str
    ).encode("utf-8")
    table = table.replace_schema_metadata(existing)
    pq.write_table(table, output, compression="snappy")


def _format_counts(values: dict[str, Any]) -> str:
    return ", ".join(
        f"{key}={value:,}" for key, value in values.items() if int(value) != 0
    ) or "none"


def write_cleaning_report(
    output: Path,
    input_path: Path,
    source_size: int,
    source_sha256: str,
    frame: pd.DataFrame,
    validation: dict[str, Any],
    model_columns: list[str],
    clean_output: Path,
    model_output: Path,
) -> None:
    ingestion = validation.get("ingestion", {})
    raw_rows = int(ingestion.get("raw_record_count", len(frame)))
    repeated = int(ingestion.get("repeated_header_count", 0))
    labels = validation["labels"]["counts"]
    nonfinite = ingestion.get("nonfinite_counts", {})
    token_counts = ingestion.get("nonfinite_tokens", {})
    timestamp = validation["timestamp"]
    report = f"""# CSE-CIC-IDS2018 Cleaning Report

Date: 2026-08-24  
Input: `{input_path}`

## Result

The raw CSV was read in chunks and was not modified.

| Measure | Value |
|---|---:|
| Raw rows after the first CSV header | {raw_rows:,} |
| Repeated header rows removed from derived data | {repeated:,} |
| Final clean records | {len(frame):,} |
| Original columns | {validation['original_column_count']:,} |
| Clean dataset columns | {validation['column_count']:,} |
| Model-safe feature columns | {len(model_columns):,} |
| Source size | {source_size:,} bytes |
| Source SHA-256 | `{source_sha256}` |

## Labels

Original labels are preserved in `Label` and `original_label`. `binary_label` is a separate modeling convenience: `Benign -> 0`, `Infilteration -> 1`. No MITRE stage mapping was created.

{_format_counts(labels)}

## Timestamp validation

- Source column: `Timestamp`
- Format: `DD/MM/YYYY HH:MM:SS`
- Parsed column: `timestamp_parsed`
- Coverage: `{timestamp['min']}` to `{timestamp['max']}`
- Invalid or missing timestamps: `{timestamp['missing_or_invalid_count']:,}`
- Chronological backsteps in source order: `{timestamp['chronological_backsteps']}`
- Timezone assumption: `{timestamp['timezone_assumption']}`

## Repeated headers and invalid values

- Duplicate header rows in the clean table: `{validation['duplicate_header_rows']}`
- Duplicate legitimate flow rows: `{validation['duplicate_rows']:,}`
- Negative durations: `{validation['negative_duration_count']:,}`
- Negative packet-count values: `{_format_counts(validation['negative_packet_counts'])}`
- Negative byte-count values: `{_format_counts(validation['negative_byte_counts'])}`
- Invalid numeric tokens after header filtering: `{_format_counts(validation['invalid_numeric_values'])}`

## Non-finite policy

All affected rate fields were verified to occur on zero-duration flows. The 4,041 `Flow Byts/s` `NaN` values also have zero total bytes; the affected rows still contain packet counts. The raw tokens are retained in `Flow Byts/s__raw` and `Flow Pkts/s__raw` provenance columns. The model-facing numeric fields are normalized to missing values, not silently replaced with zero, and both affected rate fields are excluded from the model-safe feature table.

- `Flow Byts/s`: {nonfinite.get('Flow Byts/s', 0):,} non-finite values; tokens `{token_counts.get('Flow Byts/s', {})}`
- `Flow Pkts/s`: {nonfinite.get('Flow Pkts/s', 0):,} non-finite values; tokens `{token_counts.get('Flow Pkts/s', {})}`
- Total non-finite source cells: {sum(nonfinite.values()):,}
- Non-finite values in model-safe features: 0

## Excluded model columns

The model-safe table excludes target fields, timestamps, provenance identifiers, flow-key/proxy fields, and the two non-finite rate fields. The complete exclusion rationale is in `configs/model_feature_exclusions.yaml`.

Excluded fields: `{', '.join(sorted(set(frame.columns) - set(model_columns)))}`

## Outputs

- Clean flow dataset: `{clean_output}`
- Model-safe feature dataset: `{model_output}`

## Packet-level limitation

This flow-only output does not satisfy packet-level requirements. TTL, fragmentation, retransmissions, raw packet IAT/burst ordering, packet payload distributions, complete TCP window observations, packet flag order, source IP/port, and full flow identifiers still require a matching PCAP. No packet features were fabricated.
"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")


def prepare(
    input_path: Path,
    clean_output: Path = DEFAULT_CLEAN_OUTPUT,
    model_output: Path = DEFAULT_MODEL_OUTPUT,
    report_output: Path = DEFAULT_REPORT_OUTPUT,
    exclusions_path: Path = DEFAULT_EXCLUSIONS,
) -> dict[str, Any]:
    input_path = input_path.expanduser().resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"Input CSV does not exist: {input_path}")

    frame = load_cic_ids2018_flow(input_path)
    validation = validate_flow_dataframe(frame, frame.attrs.get("ingestion_stats"))
    exclusions = load_exclusions(exclusions_path)
    model_columns = select_model_features(frame, exclusions)
    model_frame = frame[model_columns].copy()

    numeric_model = model_frame.select_dtypes(include=[np.number]).to_numpy(dtype="float64")
    if not np.isfinite(numeric_model).all():
        raise ValueError("Model-safe feature table contains non-finite values")
    if model_frame.isna().any().any():
        raise ValueError("Model-safe feature table contains missing values")

    source_size = input_path.stat().st_size
    source_sha256 = sha256_file(input_path)
    provenance = {
        "dataset": "CSE-CIC-IDS2018",
        "source_file": input_path.name,
        "source_path": str(input_path),
        "source_size_bytes": source_size,
        "source_sha256": source_sha256,
        "raw_header_columns": validation["original_column_count"],
        "raw_records_after_first_header": validation["ingestion"]["raw_record_count"],
        "repeated_header_records": validation["ingestion"]["repeated_header_count"],
        "clean_records": len(frame),
        "binary_label_mapping": {"Benign": 0, "Infilteration": 1},
        "nonfinite_policy": "raw tokens retained in __raw columns; original numeric columns normalized to NaN; affected rate columns excluded from model-safe features",
        "packet_features": "not present; requires matching PCAP",
    }
    _write_parquet(frame, clean_output, provenance | {"artifact_role": "clean_flow_dataset"})
    _write_parquet(
        model_frame,
        model_output,
        provenance
        | {
            "artifact_role": "model_safe_flow_features",
            "feature_columns": model_columns,
            "target_columns": ["Label", "original_label", "binary_label"],
        },
    )
    write_cleaning_report(
        report_output,
        input_path,
        source_size,
        source_sha256,
        frame,
        validation,
        model_columns,
        clean_output,
        model_output,
    )
    return {
        "input_path": str(input_path),
        "clean_output": str(clean_output.resolve()),
        "model_output": str(model_output.resolve()),
        "report_output": str(report_output.resolve()),
        "row_count": len(frame),
        "feature_count": len(model_columns),
        "label_counts": validation["labels"]["counts"],
        "validation": validation,
        "model_columns": model_columns,
        "source_sha256": source_sha256,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--clean-output", type=Path, default=DEFAULT_CLEAN_OUTPUT)
    parser.add_argument("--model-output", type=Path, default=DEFAULT_MODEL_OUTPUT)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--exclusions", type=Path, default=DEFAULT_EXCLUSIONS)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = prepare(
            args.input,
            args.clean_output,
            args.model_output,
            args.report_output,
            args.exclusions,
        )
    except (FileNotFoundError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"Clean records: {result['row_count']:,}")
    print(f"Model-safe feature columns: {result['feature_count']:,}")
    print(f"Clean dataset: {result['clean_output']}")
    print(f"Model features: {result['model_output']}")
    print(f"Cleaning report: {result['report_output']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
