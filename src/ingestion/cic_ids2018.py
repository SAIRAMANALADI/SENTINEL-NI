"""Deterministic, CSV-only ingestion for CSE-CIC-IDS2018 flow data."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Iterator

import numpy as np
import pandas as pd

from src.features.labels import add_label_columns
from src.features.timestamps import parse_timestamp_column


DEFAULT_CHUNKSIZE = 50_000
TIMESTAMP_COLUMN = "Timestamp"
LABEL_COLUMN = "Label"
NONFINITE_COLUMNS = ("Flow Byts/s", "Flow Pkts/s")
PROVENANCE_COLUMN = "source_row_number"
RAW_SUFFIX = "__raw"


def read_cic_header(path: str | Path) -> list[str]:
    """Read only the CSV header and return stripped column names."""
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"CSE-CIC-IDS2018 CSV does not exist: {source}")
    if source.suffix.lower() != ".csv":
        raise ValueError(f"Expected a CSV input: {source}")

    header = pd.read_csv(
        source,
        nrows=0,
        encoding="utf-8-sig",
        keep_default_na=False,
    ).columns.tolist()
    header = [str(column).strip() for column in header]
    if not header:
        raise ValueError(f"CSV has no columns: {source}")
    return header


def _is_repeated_header(chunk: pd.DataFrame, header: list[str]) -> pd.Series:
    """Match a complete repeated header row, not merely a label value."""
    expected = pd.Series(header, index=chunk.columns, dtype="object")
    return chunk.astype("string").eq(expected).all(axis=1)


def _normalize_numeric_columns(
    chunk: pd.DataFrame,
    numeric_columns: list[str],
    nonfinite_counts: Counter[str],
    nonfinite_tokens: dict[str, Counter[str]],
    numeric_parse_errors: Counter[str],
) -> None:
    """Convert numeric fields and turn non-finite values into explicit missing values."""
    for column in numeric_columns:
        raw = chunk[column].astype("string")
        numeric = pd.to_numeric(raw, errors="coerce")
        nonfinite_token_mask = raw.str.strip().str.lower().isin(
            {"nan", "infinity", "+infinity", "-infinity", "inf", "+inf", "-inf"}
        )
        parse_error_mask = numeric.isna() & raw.notna() & raw.ne("") & ~nonfinite_token_mask
        numeric_parse_errors[column] += int(parse_error_mask.sum())

        finite_values = numeric.astype("float64")
        nonfinite_mask = ~np.isfinite(finite_values.to_numpy())
        if nonfinite_mask.any():
            nonfinite_counts[column] += int(nonfinite_mask.sum())
            tokens = raw.loc[nonfinite_mask].value_counts(dropna=False)
            for token, count in tokens.items():
                nonfinite_tokens.setdefault(column, Counter())[str(token)] += int(count)
            numeric = numeric.mask(nonfinite_mask, np.nan)

        chunk[column] = numeric


def iter_cic_ids2018_flow_chunks(
    path: str | Path,
    chunksize: int = DEFAULT_CHUNKSIZE,
    preserve_source_labels: bool = False,
) -> Iterator[pd.DataFrame]:
    """Yield cleaned flow chunks without modifying the source CSV.

    Each yielded frame retains the original feature names, adds a source row
    number, preserves raw non-finite tokens in ``__raw`` columns, and adds
    parsed timestamp and label views.
    """
    source = Path(path).expanduser().resolve()
    header = read_cic_header(source)
    required = {TIMESTAMP_COLUMN, LABEL_COLUMN}
    missing = sorted(required.difference(header))
    if missing:
        raise ValueError(f"Required columns are missing: {', '.join(missing)}")

    numeric_columns = [column for column in header if column not in {TIMESTAMP_COLUMN, LABEL_COLUMN}]
    row_offset = 0
    repeated_header_count = 0
    raw_record_count = 0
    valid_record_count = 0
    reader = pd.read_csv(
        source,
        chunksize=chunksize,
        dtype="string",
        keep_default_na=False,
        na_filter=False,
        encoding="utf-8-sig",
    )
    for chunk in reader:
        raw_count = len(chunk)
        raw_record_count += raw_count
        row_numbers = pd.Series(
            range(row_offset + 1, row_offset + raw_count + 1),
            index=chunk.index,
            dtype="int64",
        )
        row_offset += raw_count

        repeated_mask = _is_repeated_header(chunk, header)
        repeated_count = int(repeated_mask.sum())
        repeated_header_count += repeated_count
        chunk = chunk.loc[~repeated_mask].copy()
        if chunk.empty:
            continue

        chunk[PROVENANCE_COLUMN] = row_numbers.loc[chunk.index].to_numpy()
        for column in NONFINITE_COLUMNS:
            if column in chunk.columns:
                chunk[f"{column}{RAW_SUFFIX}"] = chunk[column].astype("string")

        chunk_nonfinite_counts: Counter[str] = Counter()
        chunk_nonfinite_tokens: dict[str, Counter[str]] = {}
        chunk_numeric_parse_errors: Counter[str] = Counter()
        _normalize_numeric_columns(
            chunk,
            numeric_columns,
            chunk_nonfinite_counts,
            chunk_nonfinite_tokens,
            chunk_numeric_parse_errors,
        )
        chunk = parse_timestamp_column(chunk)
        if preserve_source_labels:
            chunk["original_label"] = chunk[LABEL_COLUMN].astype("string")
        else:
            chunk = add_label_columns(chunk)
        valid_record_count += len(chunk)

        chunk.attrs["ingestion_stats"] = {
            "raw_record_count": raw_count,
            "valid_record_count": len(chunk),
            "repeated_header_count": repeated_count,
            "nonfinite_counts": dict(chunk_nonfinite_counts),
            "nonfinite_tokens": {
                column: dict(tokens) for column, tokens in chunk_nonfinite_tokens.items()
            },
            "numeric_parse_errors": dict(chunk_numeric_parse_errors),
            "source_path": str(source),
            "header": header,
        }
        yield chunk

    # The aggregate values are attached to the final yielded chunk by the
    # loader below; this generator intentionally remains lazy and side-effect free.


def load_cic_ids2018_flow(
    path: str | Path,
    chunksize: int = DEFAULT_CHUNKSIZE,
    preserve_source_labels: bool = False,
) -> pd.DataFrame:
    """Load the CSV into a clean DataFrame using deterministic chunked reading."""
    frames = list(
        iter_cic_ids2018_flow_chunks(
            path,
            chunksize=chunksize,
            preserve_source_labels=preserve_source_labels,
        )
    )
    if not frames:
        raise ValueError("No legitimate flow records were found after header filtering")

    result = pd.concat(frames, ignore_index=True)
    source = Path(path).expanduser().resolve()
    header = read_cic_header(source)
    result.attrs["ingestion_stats"] = {
        "raw_record_count": int(result.attrs.get("raw_record_count", 0)),
        "valid_record_count": len(result),
        "repeated_header_count": None,
        "source_path": str(source),
        "header": header,
        "nonfinite_policy": "preserve raw token in __raw companion; normalize original numeric field to NaN; exclude affected rate fields from model-safe features",
    }
    # Aggregate from per-chunk attrs without relying on mutable generator state.
    chunk_stats = [frame.attrs.get("ingestion_stats", {}) for frame in frames]
    result.attrs["ingestion_stats"]["raw_record_count"] = int(
        sum(int(stats.get("raw_record_count", 0)) for stats in chunk_stats)
    )
    result.attrs["ingestion_stats"]["repeated_header_count"] = int(
        sum(int(stats.get("repeated_header_count", 0)) for stats in chunk_stats)
    )
    nonfinite_counts: Counter[str] = Counter()
    nonfinite_tokens: dict[str, Counter[str]] = {}
    parse_errors: Counter[str] = Counter()
    for stats in chunk_stats:
        nonfinite_counts.update(stats.get("nonfinite_counts", {}))
        parse_errors.update(stats.get("numeric_parse_errors", {}))
        for column, tokens in stats.get("nonfinite_tokens", {}).items():
            nonfinite_tokens.setdefault(column, Counter()).update(tokens)
    result.attrs["ingestion_stats"]["nonfinite_counts"] = dict(nonfinite_counts)
    result.attrs["ingestion_stats"]["nonfinite_tokens"] = {
        column: dict(tokens) for column, tokens in nonfinite_tokens.items()
    }
    result.attrs["ingestion_stats"]["numeric_parse_errors"] = dict(parse_errors)
    return result
