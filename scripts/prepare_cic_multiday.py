"""Profile and combine selected CSE-CIC-IDS2018 daily flow CSVs.

This script deliberately profiles every input completely before writing the
combined Parquet artifact. Original labels are retained without mapping.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.features.timestamps import timestamp_audit
from src.ingestion.cic_ids2018 import (
    DEFAULT_CHUNKSIZE,
    iter_cic_ids2018_flow_chunks,
    read_cic_header,
)


DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "processed" / "cic_ids2018_multiday_flow.parquet"
DEFAULT_PROFILE_DIR = PROJECT_ROOT / "results" / "day_profiles"
DEFAULT_MANIFEST = PROJECT_ROOT / "results" / "DATA_ACQUISITION_MANIFEST.json"
DEFAULT_SPLIT_REPORT = PROJECT_ROOT / "results" / "multiday_split_report.json"
DEFAULT_DIVERSITY_REPORT = PROJECT_ROOT / "results" / "TEMPORAL_DIVERSITY_REPORT.md"

SELECTED_ROLES = {
    "2018-02-14": "train",
    "2018-02-21": "train",
    "2018-02-22": "validation",
    "2018-02-28": "test",
}
EXPECTED_ATTACKS = {
    "2018-02-14": "FTP-BruteForce; SSH-Bruteforce",
    "2018-02-21": "DDoS-LOIC-UDP; DDoS-HOIC",
    "2018-02-22": "Brute Force-Web; Brute Force-XSS; SQL Injection",
    "2018-02-28": "Infiltration",
}


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def infer_capture_date(path: Path) -> str:
    match = re.search(r"(?<!\d)(\d{2})-(\d{2})-(\d{4})(?!\d)", path.name)
    if not match:
        raise ValueError(f"Could not infer capture date from filename: {path.name}")
    day, month, year = match.groups()
    return date(int(year), int(month), int(day)).isoformat()


def _merge_counts(target: Counter[str], values: Iterable[str]) -> None:
    target.update(str(value) for value in values)


def profile_day(path: Path, chunksize: int = DEFAULT_CHUNKSIZE) -> dict[str, Any]:
    """Read one complete CSV in chunks and return an auditable profile."""
    path = path.expanduser().resolve()
    header = read_cic_header(path)
    capture_date = infer_capture_date(path)
    label_counts: Counter[str] = Counter()
    missing_counts: Counter[str] = Counter()
    nonfinite_counts: Counter[str] = Counter()
    nonfinite_tokens: dict[str, Counter[str]] = {}
    numeric_parse_errors: Counter[str] = Counter()
    rows = 0
    raw_rows = 0
    repeated_headers = 0
    invalid_timestamps = 0
    min_timestamp: pd.Timestamp | None = None
    max_timestamp: pd.Timestamp | None = None
    chronological_backsteps = 0
    timestamp_capture_date_mismatches = 0
    previous_timestamp: pd.Timestamp | None = None
    expected_date = pd.Timestamp(capture_date).date()

    for chunk in iter_cic_ids2018_flow_chunks(
        path, chunksize=chunksize, preserve_source_labels=True
    ):
        stats = chunk.attrs.get("ingestion_stats", {})
        rows += len(chunk)
        raw_rows += int(stats.get("raw_record_count", 0))
        repeated_headers += int(stats.get("repeated_header_count", 0))
        label_counts.update(chunk["Label"].astype("string").tolist())
        missing_counts.update(
            {column: int(count) for column, count in chunk.isna().sum().items() if int(count)}
        )
        nonfinite_counts.update(
            {column: int(count) for column, count in stats.get("nonfinite_counts", {}).items()}
        )
        for column, tokens in stats.get("nonfinite_tokens", {}).items():
            nonfinite_tokens.setdefault(column, Counter()).update(tokens)
        numeric_parse_errors.update(stats.get("numeric_parse_errors", {}))

        timestamps = chunk["timestamp_parsed"]
        invalid_timestamps += int(timestamps.isna().sum())
        valid_timestamps = timestamps.dropna()
        if not valid_timestamps.empty:
            timestamp_capture_date_mismatches += int(
                (valid_timestamps.dt.date != expected_date).sum()
            )
            chunk_backsteps = valid_timestamps.diff().dt.total_seconds().lt(0).fillna(False)
            chronological_backsteps += int(chunk_backsteps.sum())
            first_timestamp = valid_timestamps.iloc[0]
            if previous_timestamp is not None and first_timestamp < previous_timestamp:
                chronological_backsteps += 1
            previous_timestamp = valid_timestamps.iloc[-1]
            current_min = valid_timestamps.min()
            current_max = valid_timestamps.max()
            min_timestamp = current_min if min_timestamp is None else min(min_timestamp, current_min)
            max_timestamp = current_max if max_timestamp is None else max(max_timestamp, current_max)

    if rows == 0:
        raise ValueError(f"No valid flow records found in {path}")
    return {
        "capture_date": capture_date,
        "source_file": path.name,
        "source_path": str(path),
        "source_size_bytes": path.stat().st_size,
        "source_sha256": sha256_file(path),
        "header_columns": header,
        "column_count": len(header),
        "raw_rows_after_first_header": raw_rows,
        "repeated_header_rows": repeated_headers,
        "valid_flow_rows": rows,
        "labels": dict(sorted(label_counts.items())),
        "timestamp": {
            "min": min_timestamp.isoformat(sep=" ") if min_timestamp is not None else None,
            "max": max_timestamp.isoformat(sep=" ") if max_timestamp is not None else None,
            "invalid_or_missing_count": invalid_timestamps,
            "chronological_backsteps": chronological_backsteps,
            "capture_date_mismatch_count": timestamp_capture_date_mismatches,
            "timezone_assumption": "naive local capture timestamps; no timezone conversion applied",
        },
        "missing_values": dict(sorted(missing_counts.items())),
        "nonfinite_source_values": dict(sorted(nonfinite_counts.items())),
        "nonfinite_source_tokens": {
            column: dict(sorted(tokens.items()))
            for column, tokens in sorted(nonfinite_tokens.items())
        },
        "numeric_parse_errors": dict(sorted(numeric_parse_errors.items())),
        "expected_attack_content": EXPECTED_ATTACKS.get(capture_date, "UNKNOWN"),
        "assigned_role": SELECTED_ROLES.get(capture_date, "UNASSIGNED"),
    }


def write_day_profile(profile: dict[str, Any], profile_dir: Path) -> None:
    profile_dir.mkdir(parents=True, exist_ok=True)
    stem = profile["capture_date"]
    (profile_dir / f"{stem}.json").write_text(
        json.dumps(profile, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    labels = ", ".join(
        f"`{label}`: {count:,}" for label, count in profile["labels"].items()
    )
    missing = profile["missing_values"] or {"none": 0}
    nonfinite = profile["nonfinite_source_values"] or {"none": 0}
    report = f"""# CSE-CIC-IDS2018 Day Profile: {profile['capture_date']}

- Source file: `{profile['source_file']}`
- Source size: `{profile['source_size_bytes']:,}` bytes
- SHA-256: `{profile['source_sha256']}`
- Columns: `{profile['column_count']}`
- Raw rows after first header: `{profile['raw_rows_after_first_header']:,}`
- Repeated header rows: `{profile['repeated_header_rows']:,}`
- Valid flow rows: `{profile['valid_flow_rows']:,}`
- Expected official attack content: {profile['expected_attack_content']}
- Assigned role: `{profile['assigned_role']}`

## Labels

{labels}

## Timestamp coverage

- Minimum: `{profile['timestamp']['min']}`
- Maximum: `{profile['timestamp']['max']}`
- Invalid or missing timestamps: `{profile['timestamp']['invalid_or_missing_count']:,}`
- Chronological backsteps: `{profile['timestamp']['chronological_backsteps']:,}`
- Timestamp/capture-date mismatches: `{profile['timestamp']['capture_date_mismatch_count']:,}`

## Missing and non-finite values

- Missing values after numeric normalization: `{missing}`
- Non-finite source values: `{nonfinite}`
- Original non-finite tokens: `{profile['nonfinite_source_tokens']}`
- Numeric parse errors: `{profile['numeric_parse_errors']}`

Original `Label` values are preserved. No multi-day binary mapping or model training was performed.
"""
    (profile_dir / f"{stem}.md").write_text(report, encoding="utf-8")


def _iter_provenance_chunks(path: Path, capture_date: str, chunksize: int):
    for chunk in iter_cic_ids2018_flow_chunks(
        path, chunksize=chunksize, preserve_source_labels=True
    ):
        # A column can be integer-valued in one chunk and become floating
        # point in another when a later chunk contains a missing value. Make
        # the Parquet schema deterministic before the writer is opened.
        for column in chunk.select_dtypes(include=["number"]).columns:
            chunk[column] = pd.to_numeric(chunk[column], errors="coerce").astype("float64")
        chunk["timestamp_capture_date_mismatch"] = (
            chunk["timestamp_parsed"].dt.date != pd.Timestamp(capture_date).date()
        )
        chunk["source_file"] = path.name
        chunk["capture_date"] = capture_date
        yield chunk


def build_multiday_parquet(
    sources: list[Path],
    profiles: list[dict[str, Any]],
    output: Path,
    chunksize: int,
) -> None:
    """Write a provenance-preserving Parquet file after all profiles pass."""
    if len({tuple(profile["header_columns"]) for profile in profiles}) != 1:
        raise ValueError("Selected CSV headers are not identical; merge was not attempted")
    output.parent.mkdir(parents=True, exist_ok=True)
    writer: pq.ParquetWriter | None = None
    try:
        for source, profile in zip(sources, profiles, strict=True):
            for chunk in _iter_provenance_chunks(source, profile["capture_date"], chunksize):
                table = pa.Table.from_pandas(chunk, preserve_index=False)
                if writer is None:
                    writer = pq.ParquetWriter(output, table.schema, compression="snappy")
                elif table.schema != writer.schema:
                    table = table.cast(writer.schema)
                writer.write_table(table)
    finally:
        if writer is not None:
            writer.close()
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError(f"Multi-day Parquet output was not created: {output}")


def build_manifest(profiles: list[dict[str, Any]]) -> dict[str, Any]:
    objects = []
    for profile in profiles:
        objects.append(
            {
                "capture_date": profile["capture_date"],
                "source_file": profile["source_file"],
                "s3_key": f"Processed Traffic Data for ML Algorithms/{profile['source_file']}",
                "s3_uri": f"s3://cse-cic-ids2018/Processed Traffic Data for ML Algorithms/{profile['source_file']}",
                "local_path": str(Path(profile["source_path"]).resolve().relative_to(PROJECT_ROOT)),
                "source_size_bytes": profile["source_size_bytes"],
                "source_sha256": profile["source_sha256"],
                "assigned_role": profile["assigned_role"],
                "expected_attack_content": profile["expected_attack_content"],
                "downloaded_or_present": True,
            }
        )
    return {
        "dataset": "CSE-CIC-IDS2018",
        "source_url": "https://www.unb.ca/cic/datasets/ids-2018.html",
        "aws_registry_url": "https://registry.opendata.aws/cse-cic-ids2018/",
        "bucket": "s3://cse-cic-ids2018",
        "inventory_prefix": "Processed Traffic Data for ML Algorithms/",
        "access_method": "aws s3 cp --no-sign-request",
        "acquisition_date": date.today().isoformat(),
        "pcap_downloaded": False,
        "objects": sorted(objects, key=lambda item: item["capture_date"]),
        "selection_note": "Smallest selected set supporting two training days, a separate validation day, and existing 28-Feb unseen test day/scenario.",
    }


def build_split_report(profiles: list[dict[str, Any]]) -> dict[str, Any]:
    by_role: dict[str, list[dict[str, Any]]] = {"train": [], "validation": [], "test": []}
    for profile in profiles:
        role = profile["assigned_role"]
        if role not in by_role:
            raise ValueError(f"Unassigned capture date in selected set: {profile['capture_date']}")
        by_role[role].append(profile)
    split_rows = {}
    split_labels = {}
    for role, role_profiles in by_role.items():
        labels: Counter[str] = Counter()
        rows = 0
        timestamp_mismatches = 0
        for profile in role_profiles:
            rows += profile["valid_flow_rows"]
            labels.update(profile["labels"])
            timestamp_mismatches += profile["timestamp"]["capture_date_mismatch_count"]
        split_rows[role] = {
            "capture_dates": [p["capture_date"] for p in sorted(role_profiles, key=lambda p: p["capture_date"])],
            "rows": rows,
            "labels": dict(sorted(labels.items())),
            "timestamp_capture_date_mismatch_rows": timestamp_mismatches,
        }
        split_labels[role] = dict(sorted(labels.items()))
    ordered = sorted(profiles, key=lambda p: p["capture_date"])
    return {
        "method": "complete capture-day assignment; no random row distribution",
        "random_row_split_used": False,
        "train_days": split_rows["train"]["capture_dates"],
        "validation_days": split_rows["validation"]["capture_dates"],
        "test_days": split_rows["test"]["capture_dates"],
        "split_rows": split_rows,
        "label_distribution_by_split": split_labels,
        "ordered_capture_dates": [p["capture_date"] for p in ordered],
        "dataset_min_timestamp": min(p["timestamp"]["min"] for p in profiles),
        "dataset_max_timestamp": max(p["timestamp"]["max"] for p in profiles),
        "observed_timestamp_range": {
            "min": min(p["timestamp"]["min"] for p in profiles),
            "max": max(p["timestamp"]["max"] for p in profiles),
        },
        "capture_date_range": {
            "min": min(p["capture_date"] for p in profiles),
            "max": max(p["capture_date"] for p in profiles),
        },
        "timestamp_capture_date_mismatches_by_day": {
            p["capture_date"]: p["timestamp"]["capture_date_mismatch_count"]
            for p in profiles
        },
        "within_day_timestamp_ordering_ready": all(
            p["timestamp"]["capture_date_mismatch_count"] == 0 for p in profiles
        ),
        "day_boundary_gap_policy": "no rows cross day assignments; within-day rows remain ordered by parsed timestamp and source row number",
        "source_file_and_capture_date_model_policy": "retained as provenance metadata and excluded from model features by default",
    }


def write_diversity_report(profiles: list[dict[str, Any]], split_report: dict[str, Any], output: Path) -> None:
    train_labels = set(split_report["label_distribution_by_split"]["train"])
    test_labels = set(split_report["label_distribution_by_split"]["test"])
    absent_from_train = sorted(test_labels - train_labels)
    lines = [
        "# CSE-CIC-IDS2018 Temporal Diversity Report",
        "",
        "## Result",
        "",
        "The selected four-day flow collection supports a chronological day-separated experiment. It is not a world-model result and no model was trained.",
        "",
        "## Coverage",
        "",
        f"- Distinct capture days: `{len(profiles)}`",
        f"- Capture-date span: `{split_report['capture_date_range']['min']}` to `{split_report['capture_date_range']['max']}`",
        f"- Observed flow timestamp span (including anomalies): `{split_report['observed_timestamp_range']['min']}` to `{split_report['observed_timestamp_range']['max']}`",
        f"- Total valid flow rows: `{sum(p['valid_flow_rows'] for p in profiles):,}`",
        f"- Timestamp/capture-date mismatches: `{sum(split_report['timestamp_capture_date_mismatches_by_day'].values()):,}`",
        f"- Test labels absent from training labels: `{absent_from_train}`",
        "",
        "| Capture date | Role | Rows | Timestamp range | Labels | Officially documented activity |",
        "|---|---|---:|---|---|---|",
    ]
    for profile in sorted(profiles, key=lambda p: p["capture_date"]):
        labels = "; ".join(f"{key}: {value:,}" for key, value in profile["labels"].items())
        lines.append(
            f"| {profile['capture_date']} | {profile['assigned_role']} | {profile['valid_flow_rows']:,} | "
            f"{profile['timestamp']['min']} to {profile['timestamp']['max']} | {labels} | {profile['expected_attack_content']} |"
        )
    lines.extend(
        [
            "",
            "## Temporal split",
            "",
            f"- Train days: `{split_report['train_days']}`",
            f"- Validation days: `{split_report['validation_days']}`",
            f"- Test days: `{split_report['test_days']}`",
            "- Rows were not randomly distributed across days.",
            "- `source_file` and `capture_date` are provenance fields, not model features.",
            "",
            "## Interpretation",
            "",
            "The test day is later than both training and validation and contains the documented Infiltration condition, which is absent from the training-day label set in the observed flow labels. This gives a meaningful unseen-day/unseen-condition test, but it does not prove generalization beyond this four-day slice. The official schedule documents attack content; the label counts above are measured from the CSVs.",
            "",
            "Fourteen rows have parseable but capture-date-inconsistent January 1970 timestamps (5 on 14-Feb and 9 on 22-Feb). They are retained with their original timestamp and an explicit `timestamp_capture_date_mismatch` flag. Timestamp-based within-day ordering is not ready until these rows are handled by a documented exclusion or source-correction decision.",
            "",
            "Remaining gaps: fixed-interval network-state aggregation, matching PCAP-derived features, more independent days/scenarios for robustness, and a future model evaluation. No model was trained in this task.",
        ]
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="append", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--profile-dir", type=Path, default=DEFAULT_PROFILE_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--split-report", type=Path, default=DEFAULT_SPLIT_REPORT)
    parser.add_argument("--diversity-report", type=Path, default=DEFAULT_DIVERSITY_REPORT)
    parser.add_argument("--chunksize", type=int, default=DEFAULT_CHUNKSIZE)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    sources = [path.expanduser().resolve() for path in args.source]
    try:
        profiles = [profile_day(path, chunksize=args.chunksize) for path in sources]
        dates = [profile["capture_date"] for profile in profiles]
        if len(set(dates)) != len(dates):
            raise ValueError("Selected sources contain duplicate capture dates")
        if set(dates) != set(SELECTED_ROLES):
            raise ValueError(f"Selected dates must be exactly {sorted(SELECTED_ROLES)}; got {sorted(dates)}")
        headers = {tuple(profile["header_columns"]) for profile in profiles}
        if len(headers) != 1:
            raise ValueError("Selected files have incompatible headers; merge was not attempted")
        for profile in profiles:
            write_day_profile(profile, args.profile_dir)
        build_multiday_parquet(sources, profiles, args.output, args.chunksize)
        manifest = build_manifest(profiles)
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        split_report = build_split_report(profiles)
        args.split_report.parent.mkdir(parents=True, exist_ok=True)
        args.split_report.write_text(json.dumps(split_report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        write_diversity_report(profiles, split_report, args.diversity_report)
    except (FileNotFoundError, ValueError, TypeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Profiled days: {dates}")
    print(f"Total valid rows: {sum(profile['valid_flow_rows'] for profile in profiles):,}")
    print(f"Multi-day Parquet: {args.output.resolve()}")
    print(f"Manifest: {args.manifest.resolve()}")
    print(f"Split report: {args.split_report.resolve()}")
    print(f"Diversity report: {args.diversity_report.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
