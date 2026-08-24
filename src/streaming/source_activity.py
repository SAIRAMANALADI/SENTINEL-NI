"""Deterministic source activity aggregation for packet/event streams.

This module is an input adapter only. It does not read PCAP files, infer
attackers, or emit a source-level probability. Reverse packets are grouped
with a direction-independent canonical flow key for ``flow_count`` while the
observed ``source_ip`` remains the source identity for the activity row.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import numpy as np
import pandas as pd


PACKET_EVENT_COLUMNS = [
    "timestamp",
    "source_ip",
    "destination_ip",
    "source_port",
    "destination_port",
    "protocol",
    "packet_length",
    "tcp_flags",
]

SOURCE_ACTIVITY_COLUMNS = [
    "source_ip",
    "capture_day",
    "interval_start",
    "interval_end",
    "flow_count",
    "packet_count",
    "byte_count",
    "unique_destinations",
    "unique_destination_ports",
    "mean_packet_size",
    "mean_iat",
    "syn_count",
    "ack_count",
    "rst_count",
    "packet_rate",
    "byte_rate",
]


def _flag_tokens(value: Any) -> frozenset[str]:
    """Normalize common textual TCP flag representations without guessing bits."""

    if value is None or (isinstance(value, float) and np.isnan(value)):
        return frozenset()
    if isinstance(value, (list, tuple, set, frozenset)):
        raw = " ".join(str(item) for item in value)
    else:
        raw = str(value)
    raw = raw.upper().replace("|", " ").replace(",", " ").replace("/", " ")
    aliases = {"S": "SYN", "A": "ACK", "R": "RST"}
    return frozenset(aliases.get(token, token) for token in raw.split() if token)


def _numeric_port(frame: pd.DataFrame, column: str) -> pd.Series:
    values = pd.to_numeric(frame[column], errors="coerce")
    if values.isna().any() or not np.isfinite(values.to_numpy(dtype="float64")).all():
        raise ValueError(f"packet event column {column!r} contains a non-finite port")
    if (values % 1 != 0).any() or values.lt(0).any() or values.gt(65535).any():
        raise ValueError(f"packet event column {column!r} must contain integer ports in [0, 65535]")
    return values.astype("int64")


def normalize_packet_events(events: Iterable[Mapping[str, Any]] | pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize packet events while preserving observed values."""

    if isinstance(events, pd.DataFrame):
        frame = events.copy()
    else:
        frame = pd.DataFrame(list(events))
    if frame.empty:
        return pd.DataFrame(columns=PACKET_EVENT_COLUMNS)

    missing = [column for column in PACKET_EVENT_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"packet events are missing required fields: {missing}")
    result = frame.copy()
    result["timestamp"] = pd.to_datetime(result["timestamp"], errors="coerce", format="mixed")
    if result["timestamp"].isna().any():
        raise ValueError("packet events contain invalid timestamps")
    for column in ("source_ip", "destination_ip", "protocol"):
        result[column] = result[column].astype("string")
        if result[column].isna().any() or result[column].str.strip().eq("").any():
            raise ValueError(f"packet event column {column!r} contains a missing value")
    result["source_port"] = _numeric_port(result, "source_port")
    result["destination_port"] = _numeric_port(result, "destination_port")
    result["packet_length"] = pd.to_numeric(result["packet_length"], errors="coerce")
    if result["packet_length"].isna().any() or not np.isfinite(result["packet_length"].to_numpy(dtype="float64")).all():
        raise ValueError("packet_length must be finite")
    if result["packet_length"].lt(0).any():
        raise ValueError("packet_length must be non-negative")
    result["tcp_flags"] = result["tcp_flags"].map(_flag_tokens)
    return result.reset_index(drop=True)


def flow_5tuple(event: Mapping[str, Any]) -> tuple[str, str, int, int, str]:
    """Return the observed-direction five-tuple required by the source contract."""

    normalized = normalize_packet_events([event]).iloc[0]
    return (
        str(normalized["source_ip"]),
        str(normalized["destination_ip"]),
        int(normalized["source_port"]),
        int(normalized["destination_port"]),
        str(normalized["protocol"]).upper(),
    )


def canonical_flow_5tuple(event: Mapping[str, Any]) -> tuple[str, int, str, int, str]:
    """Return a direction-independent key for grouping forward/reverse packets."""

    observed = flow_5tuple(event)
    source_endpoint = (observed[0], observed[2])
    destination_endpoint = (observed[1], observed[3])
    first, second = sorted((source_endpoint, destination_endpoint))
    return (first[0], first[1], second[0], second[1], observed[4])


def _empty_activity_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=SOURCE_ACTIVITY_COLUMNS)


def aggregate_source_activity(
    events: Iterable[Mapping[str, Any]] | pd.DataFrame,
    interval_seconds: int = 10,
) -> pd.DataFrame:
    """Aggregate observed packet events by source and fixed interval.

    Input rows are stably sorted by timestamp, so deterministic replay can
    provide out-of-order rows to this batch adapter. Duplicate input rows are
    retained as observed packets because the minimum event schema has no
    packet identifier or deduplication contract.
    """

    if isinstance(interval_seconds, bool) or not isinstance(interval_seconds, int) or interval_seconds <= 0:
        raise ValueError("interval_seconds must be a positive integer")
    frame = normalize_packet_events(events)
    if frame.empty:
        return _empty_activity_frame()
    frame = frame.sort_values("timestamp", kind="mergesort").reset_index(drop=True)
    frequency = f"{interval_seconds}s"
    frame["capture_day"] = frame["timestamp"].dt.strftime("%Y-%m-%d")
    frame["interval_start"] = frame["timestamp"].dt.floor(frequency)
    frame["_canonical_flow"] = [canonical_flow_5tuple(row) for row in frame.to_dict(orient="records")]

    rows: list[dict[str, Any]] = []
    group_columns = ["capture_day", "interval_start", "source_ip"]
    for (capture_day, interval_start, source_ip), group in frame.groupby(group_columns, sort=True, observed=True):
        timestamps = group["timestamp"].sort_values(kind="mergesort")
        iats = timestamps.diff().dt.total_seconds().dropna()
        flag_values = group["tcp_flags"]
        packet_count = int(len(group))
        byte_count = float(group["packet_length"].sum())
        rows.append(
            {
                "source_ip": str(source_ip),
                "capture_day": str(capture_day),
                "interval_start": pd.Timestamp(interval_start),
                "interval_end": pd.Timestamp(interval_start) + pd.Timedelta(seconds=interval_seconds),
                "flow_count": int(group["_canonical_flow"].nunique()),
                "packet_count": packet_count,
                "byte_count": byte_count,
                "unique_destinations": int(group["destination_ip"].nunique()),
                "unique_destination_ports": int(group["destination_port"].nunique()),
                "mean_packet_size": float(group["packet_length"].mean()),
                "mean_iat": float(iats.mean()) if not iats.empty else 0.0,
                "syn_count": int(flag_values.map(lambda value: "SYN" in value).sum()),
                "ack_count": int(flag_values.map(lambda value: "ACK" in value).sum()),
                "rst_count": int(flag_values.map(lambda value: "RST" in value).sum()),
                "packet_rate": packet_count / float(interval_seconds),
                "byte_rate": byte_count / float(interval_seconds),
            }
        )
    return pd.DataFrame(rows, columns=SOURCE_ACTIVITY_COLUMNS).sort_values(
        ["interval_start", "source_ip"], kind="mergesort"
    ).reset_index(drop=True)


class SourceActivityAccumulator:
    """Streaming adapter that emits one completed source table per interval."""

    def __init__(self, interval_seconds: int = 10) -> None:
        if isinstance(interval_seconds, bool) or not isinstance(interval_seconds, int) or interval_seconds <= 0:
            raise ValueError("interval_seconds must be a positive integer")
        self.interval_seconds = interval_seconds
        self._bucket: pd.Timestamp | None = None
        self._events: list[dict[str, Any]] = []
        self._last_timestamp: pd.Timestamp | None = None

    def feed(self, event: Mapping[str, Any]) -> pd.DataFrame | None:
        normalized = normalize_packet_events([event])
        timestamp = pd.Timestamp(normalized.iloc[0]["timestamp"])
        if self._last_timestamp is not None and timestamp < self._last_timestamp:
            raise ValueError("source packet replay events must be chronological")
        self._last_timestamp = timestamp
        bucket = timestamp.floor(f"{self.interval_seconds}s")
        completed: pd.DataFrame | None = None
        if self._bucket is None:
            self._bucket = bucket
        elif bucket != self._bucket:
            if bucket < self._bucket:
                raise ValueError("source packet replay interval moved backwards")
            completed = aggregate_source_activity(self._events, self.interval_seconds)
            self._events = []
            self._bucket = bucket
        self._events.append(normalized.iloc[0].to_dict())
        return completed

    def flush(self) -> pd.DataFrame | None:
        if not self._events:
            return None
        completed = aggregate_source_activity(self._events, self.interval_seconds)
        self._events = []
        self._bucket = None
        return completed
