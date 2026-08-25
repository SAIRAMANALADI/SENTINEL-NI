"""End-to-end offline demonstration orchestration.

The engine composes existing source aggregation, frozen network-state
aggregation, state buffering, inference, source prioritization, and mitigation
policy components. It contains no model mathematics, preprocessing, or second
policy implementation.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from src.evaluation.mitigation_policy import recommendations_for_sources
from src.forecasting.inference import predict_network_state_sequence
from src.streaming.source_activity import aggregate_source_activity
from src.streaming.source_forecast import prioritize_sources_with_forecast
from src.streaming.state_aggregator import aggregate_flow_window
from src.streaming.state_buffer import BufferUpdate, StateBuffer


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INTERVAL_SECONDS = 10
DEFAULT_SEQUENCE_LENGTH = 10

FLOW_REQUIRED_COLUMNS = {
    "timestamp",
    "capture_date",
    "Label",
    "Dst Port",
    "Flow Duration",
    "Tot Fwd Pkts",
    "Tot Bwd Pkts",
    "TotLen Fwd Pkts",
    "TotLen Bwd Pkts",
    "Flow IAT Mean",
    "Flow IAT Std",
    "SYN Flag Cnt",
    "ACK Flag Cnt",
    "RST Flag Cnt",
    "Pkt Len Mean",
    "Pkt Len Std",
}
PACKET_REQUIRED_COLUMNS = {
    "timestamp",
    "source_ip",
    "destination_ip",
    "source_port",
    "destination_port",
    "protocol",
    "packet_length",
    "tcp_flags",
}

InferenceFunction = Callable[[pd.DataFrame], dict[str, Any]]


def load_demo_events(path: str | Path) -> pd.DataFrame:
    """Load and validate the combined synthetic flow/packet demo events."""

    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"final demo event file does not exist: {source}")
    frame = pd.read_csv(source, comment="#")
    missing = sorted((FLOW_REQUIRED_COLUMNS | PACKET_REQUIRED_COLUMNS).difference(frame.columns))
    if missing:
        raise ValueError(f"final demo events are missing required fields: {missing}")
    if "demo_status" not in frame.columns:
        raise ValueError("final demo events must declare demo_status")
    statuses = frame["demo_status"].astype(str).unique().tolist()
    if statuses != ["DEMO / TEST DATA - NOT RESEARCH DATA"]:
        raise ValueError("final demo events must be explicitly marked as demo/test data")
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce", format="mixed")
    if frame["timestamp"].isna().any():
        raise ValueError("final demo events contain invalid timestamps")
    frame["capture_date"] = frame["capture_date"].astype(str)
    if frame["timestamp"].dt.strftime("%Y-%m-%d").ne(frame["capture_date"]).any():
        raise ValueError("final demo timestamps do not belong to capture_date")
    frame = frame.sort_values("timestamp", kind="mergesort").reset_index(drop=True)
    return frame


def _json_safe(value: Any) -> Any:
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "item"):
        return _json_safe(value.item())
    return value


def _network_result(result: dict[str, Any]) -> dict[str, Any]:
    """Select the actual inference output needed by the integrated contract."""

    return {
        "model_version": result["model_version"],
        "forecast_horizon_seconds": int(result["forecast_horizon_seconds"]),
        "forecasts": [
            {
                "step": int(row["step"]),
                "horizon_seconds": int(row["horizon_seconds"]),
                "timestamp": row["timestamp"],
                "score": float(row["score"]),
                "warning": bool(row["warning"]),
            }
            for row in result["forecast"]
        ],
        "operating_mode": result["operating_mode"],
        "threshold": float(result["threshold"]),
        "explanation": result["explanation"],
        "reference_timestamp": result["reference_timestamp"],
    }


class FinalDemoEngine:
    """Run the deterministic source/network/forecast demonstration offline."""

    def __init__(
        self,
        *,
        sequence_length: int = DEFAULT_SEQUENCE_LENGTH,
        interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
        inference_fn: InferenceFunction = predict_network_state_sequence,
    ) -> None:
        if sequence_length != DEFAULT_SEQUENCE_LENGTH:
            raise ValueError("the frozen final demo requires sequence_length=10")
        if interval_seconds != DEFAULT_INTERVAL_SECONDS:
            raise ValueError("the frozen final demo requires interval_seconds=10")
        self.sequence_length = sequence_length
        self.interval_seconds = interval_seconds
        self.inference_fn = inference_fn

    def run(self, events: pd.DataFrame | Iterable[Mapping[str, Any]]) -> dict[str, Any]:
        started = time.perf_counter()
        frame = events if isinstance(events, pd.DataFrame) else pd.DataFrame(list(events))
        if frame.empty:
            raise ValueError("final demo requires at least one event")
        # Validate the same combined event contract used by the file loader.
        missing = sorted((FLOW_REQUIRED_COLUMNS | PACKET_REQUIRED_COLUMNS).difference(frame.columns))
        if missing:
            raise ValueError(f"final demo events are missing required fields: {missing}")
        frame = frame.copy()
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], errors="coerce", format="mixed")
        if frame["timestamp"].isna().any():
            raise ValueError("final demo events contain invalid timestamps")
        frame = frame.sort_values("timestamp", kind="mergesort").reset_index(drop=True)
        capture_days = frame["timestamp"].dt.strftime("%Y-%m-%d").unique()
        if len(capture_days) != 1:
            raise ValueError("final demo must use one capture day")

        buffer = StateBuffer(sequence_length=self.sequence_length, interval_seconds=self.interval_seconds)
        current_bucket: pd.Timestamp | None = None
        flow_bucket: list[dict[str, Any]] = []
        packet_bucket: list[dict[str, Any]] = []
        activity_frames: list[pd.DataFrame] = []
        latest_inference: dict[str, Any] | None = None
        source_ms = 0.0
        state_ms = 0.0
        inference_ms = 0.0

        def flush_bucket() -> None:
            nonlocal current_bucket, flow_bucket, packet_bucket, latest_inference
            nonlocal source_ms, state_ms, inference_ms
            if not flow_bucket:
                return
            source_started = time.perf_counter()
            activity_frames.append(aggregate_source_activity(packet_bucket, self.interval_seconds))
            source_ms += (time.perf_counter() - source_started) * 1000

            state_started = time.perf_counter()
            state = aggregate_flow_window(flow_bucket, interval_seconds=self.interval_seconds)
            state_ms += (time.perf_counter() - state_started) * 1000
            update: BufferUpdate = buffer.push(state)
            if update.sequence is not None:
                inference_started = time.perf_counter()
                latest_inference = dict(self.inference_fn(update.sequence))
                inference_ms += (time.perf_counter() - inference_started) * 1000
            current_bucket = None
            flow_bucket = []
            packet_bucket = []

        for row in frame.to_dict(orient="records"):
            timestamp = pd.Timestamp(row["timestamp"])
            bucket = timestamp.floor(f"{self.interval_seconds}s")
            if current_bucket is None:
                current_bucket = bucket
            elif bucket != current_bucket:
                flush_bucket()
                current_bucket = bucket
            flow_bucket.append(row)
            packet_bucket.append(row)
        flush_bucket()

        if latest_inference is None:
            raise ValueError(
                f"final demo produced fewer than {self.sequence_length} valid 10-second states; "
                "provide at least 10 complete chronological intervals"
            )

        network = _network_result(latest_inference)
        activity = pd.concat(activity_frames, ignore_index=True)
        priority_started = time.perf_counter()
        all_priorities = prioritize_sources_with_forecast(activity, latest_inference)
        latest_by_source: dict[str, dict[str, Any]] = {}
        for row in all_priorities:
            latest_by_source[str(row["source_ip"])] = row
        source_priorities = sorted(latest_by_source.values(), key=lambda row: row["source_ip"])
        priority_ms = (time.perf_counter() - priority_started) * 1000

        mitigation_started = time.perf_counter()
        mitigation = recommendations_for_sources(source_priorities)
        mitigation_ms = (time.perf_counter() - mitigation_started) * 1000

        result = {
            "timestamp": network["reference_timestamp"],
            "network_forecast": network,
            "network_status": "Predictive warning" if network["forecasts"][0]["warning"] else "No predictive warning",
            "source_priorities": source_priorities,
            "mitigation_recommendations": mitigation,
            "processing_time_ms": float((time.perf_counter() - started) * 1000),
            "timing_ms": {
                "source_activity": float(source_ms),
                "network_state": float(state_ms),
                "inference": float(inference_ms),
                "source_prioritization": float(priority_ms),
                "mitigation": float(mitigation_ms),
                "total": float((time.perf_counter() - started) * 1000),
            },
            "state_count": len(activity_frames),
            "history_length": self.sequence_length,
            "simulation_only": True,
            "pcap_attribution_validated": False,
        }
        return _json_safe(result)


def run_final_demo(path: str | Path) -> dict[str, Any]:
    """Load the approved synthetic event file and execute the final demo."""

    return FinalDemoEngine().run(load_demo_events(path))


def assert_json_serializable(result: Mapping[str, Any]) -> None:
    """Raise a clear error if an integration result leaves non-JSON values."""

    json.dumps(result, allow_nan=False)
