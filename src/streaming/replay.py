"""Deterministic offline replay sources for state and flow artifacts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from itertools import islice
from pathlib import Path
from typing import Any, Iterator

import pandas as pd

from src.ingestion.cic_ids2018 import iter_cic_ids2018_flow_chunks, read_cic_header
from src.streaming.state_aggregator import STATE_COLUMNS, validate_state


@dataclass(frozen=True)
class ReplayEvent:
    """One chronological replay input event."""

    timestamp: pd.Timestamp
    capture_day: str
    kind: str
    payload: dict[str, Any]


def _read_state_frame(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        frame = pd.read_parquet(path)
    elif path.suffix.lower() in {".csv", ".tsv"}:
        frame = pd.read_csv(path, sep="\t" if path.suffix.lower() == ".tsv" else ",")
    else:
        raise ValueError("replay input must be .csv, .tsv, or .parquet")
    return validate_state(frame[STATE_COLUMNS] if set(STATE_COLUMNS).issubset(frame.columns) else frame)


def _state_events(frame: pd.DataFrame) -> Iterator[ReplayEvent]:
    previous: pd.Timestamp | None = None
    for row in frame.to_dict(orient="records"):
        timestamp = pd.Timestamp(row["timestamp"])
        if previous is not None and timestamp <= previous:
            raise ValueError("replay state source must be strictly chronological")
        previous = timestamp
        yield ReplayEvent(
            timestamp=timestamp,
            capture_day=str(row["capture_day"]),
            kind="state",
            payload={column: row[column] for column in STATE_COLUMNS},
        )


def _capture_date_from_filename(path: Path) -> str | None:
    match = re.search(r"(?<!\d)(\d{2})-(\d{2})-(\d{4})(?!\d)", path.name)
    if not match:
        return None
    day, month, year = match.groups()
    return f"{year}-{month}-{day}"


def _flow_events(path: Path, max_events: int | None) -> Iterator[ReplayEvent]:
    header = read_cic_header(path)
    expected_capture_day = _capture_date_from_filename(path)
    previous: pd.Timestamp | None = None
    emitted = 0
    for chunk in iter_cic_ids2018_flow_chunks(path, preserve_source_labels=True):
        for row in chunk.to_dict(orient="records"):
            timestamp = pd.Timestamp(row["timestamp_parsed"])
            if pd.isna(timestamp):
                raise ValueError("flow replay source contains an invalid timestamp")
            capture_day = expected_capture_day or timestamp.strftime("%Y-%m-%d")
            if timestamp.strftime("%Y-%m-%d") != capture_day:
                raise ValueError("flow replay timestamp does not belong to the capture day")
            if previous is not None and timestamp < previous:
                raise ValueError("flow replay source must be chronologically ordered")
            previous = timestamp
            payload = dict(row)
            payload["capture_date"] = capture_day
            yield ReplayEvent(timestamp, capture_day, "flow", payload)
            emitted += 1
            if max_events is not None and emitted >= max_events:
                return
    if not header:
        raise ValueError("replay source has no columns")


def iter_replay_events(path: str | Path, max_events: int | None = None) -> Iterator[ReplayEvent]:
    """Yield state or raw-flow events in source order without timestamp rewriting."""

    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"replay source does not exist: {source}")
    if max_events is not None and (isinstance(max_events, bool) or max_events < 1):
        raise ValueError("max_events must be positive when provided")

    if source.suffix.lower() == ".parquet":
        frame = pd.read_parquet(source)
        if set(STATE_COLUMNS).issubset(frame.columns):
            events = _state_events(validate_state(frame[STATE_COLUMNS]))
            yield from islice(events, max_events)
            return
        raise ValueError("Parquet replay sources must contain the frozen state columns")

    header = read_cic_header(source)
    if set(STATE_COLUMNS).issubset(header):
        frame = _read_state_frame(source)
        events = _state_events(frame)
        for index, event in enumerate(events):
            if max_events is not None and index >= max_events:
                break
            yield event
        return
    if {"Timestamp", "Label"}.issubset(header):
        yield from _flow_events(source, max_events)
        return
    raise ValueError("replay source is neither an approved state file nor a CSE-CIC-IDS2018 flow file")


def iter_packet_replay_events(path: str | Path, max_events: int | None = None) -> Iterator[ReplayEvent]:
    """Yield deterministic JSONL packet events for the source-attribution adapter."""

    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"packet replay source does not exist: {source}")
    if source.suffix.lower() not in {".jsonl", ".ndjson", ".json"}:
        raise ValueError("packet replay source must be .jsonl, .ndjson, or .json")
    emitted = 0
    previous: pd.Timestamp | None = None
    with source.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid packet replay JSON on line {line_number}") from exc
            if not isinstance(payload, dict):
                raise ValueError(f"packet replay line {line_number} must contain an object")
            timestamp = pd.to_datetime(payload.get("timestamp"), errors="coerce", format="mixed")
            if pd.isna(timestamp):
                raise ValueError(f"packet replay line {line_number} has an invalid timestamp")
            timestamp = pd.Timestamp(timestamp)
            if previous is not None and timestamp < previous:
                raise ValueError("packet replay source must be chronologically ordered")
            previous = timestamp
            capture_day = str(payload.get("capture_day") or timestamp.strftime("%Y-%m-%d"))
            if timestamp.strftime("%Y-%m-%d") != capture_day:
                raise ValueError(f"packet replay line {line_number} timestamp does not belong to capture_day")
            payload.pop("capture_day", None)
            yield ReplayEvent(timestamp, capture_day, "packet", payload)
            emitted += 1
            if max_events is not None and emitted >= max_events:
                return
