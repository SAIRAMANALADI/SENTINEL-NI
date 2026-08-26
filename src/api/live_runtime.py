"""Bounded API-owned runtime state for live packet-to-forecast operation."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from threading import RLock
import time
from typing import Any

import numpy as np
import pandas as pd

from src.evaluation.mitigation_policy import recommendations_for_sources
from src.features.network_state import FEATURE_COLUMNS, build_network_state_for_inference
from src.forecasting.inference import predict_network_state_sequence
from src.streaming.flow_builder import FlowBuilder, FlowBuilderError, FlowTableOverflowError
from src.streaming.source_activity import SourceActivityAccumulator
from src.streaming.source_forecast import prioritize_sources, prioritize_sources_with_forecast
from src.streaming.state_aggregator import STATE_COLUMNS
from src.streaming.state_buffer import StateBuffer


InferenceFunction = Callable[[pd.DataFrame], dict[str, Any]]


class LiveRuntimeStore:
    """Keep only the bounded operational state needed by API and dashboard."""

    def __init__(
        self,
        *,
        sequence_length: int = 10,
        interval_seconds: int = 10,
        max_flow_records: int = 4096,
        max_state_records: int = 128,
        max_activity_frames: int = 64,
        inference_fn: InferenceFunction = predict_network_state_sequence,
    ) -> None:
        if sequence_length != 10:
            raise ValueError("live runtime requires sequence_length=10")
        if interval_seconds != 10:
            raise ValueError("live runtime requires interval_seconds=10")
        if min(max_flow_records, max_state_records, max_activity_frames) < 1:
            raise ValueError("live runtime bounds must be positive")
        self.sequence_length = sequence_length
        self.interval_seconds = interval_seconds
        self.max_flow_records = max_flow_records
        self.max_state_records = max_state_records
        self.max_activity_frames = max_activity_frames
        self._inference_fn = inference_fn
        self._lock = RLock()
        self._last_forecast: dict[str, Any] | None = None
        self._stale_forecast: dict[str, Any] | None = None
        self._last_error: str | None = None
        self._reset_active_state()

    def _reset_active_state(self) -> None:
        self._flow_builder = FlowBuilder()
        self._state_buffer = StateBuffer(
            sequence_length=self.sequence_length,
            interval_seconds=self.interval_seconds,
        )
        self._source_accumulator = SourceActivityAccumulator(self.interval_seconds)
        self._completed_flows: deque[dict[str, Any]] = deque(maxlen=self.max_flow_records)
        self._state_rows: deque[dict[str, Any]] = deque(maxlen=self.max_state_records)
        self._state_keys: set[tuple[str, str]] = set()
        self._activity_frames: deque[pd.DataFrame] = deque(maxlen=self.max_activity_frames)
        self._event_count = 0
        self._accepted_event_count = 0
        self._rejected_event_count = 0
        self._rejected_event_categories: dict[str, int] = {}
        self._last_rejection_reason: str | None = None
        self._completed_flow_count = 0
        self._state_count = 0
        self._buffer_fill = 0
        self._latest_state_timestamp: pd.Timestamp | None = None
        self._forecast_update_count = 0
        self._source_priorities: list[dict[str, Any]] = []
        self._mitigation_recommendations: list[dict[str, Any]] = []
        self._session_started_at = datetime.now(timezone.utc).isoformat()
        self._session_started_monotonic = time.perf_counter()
        self._startup_stage_timestamps: dict[str, str] = {}

    def start_session(self) -> None:
        """Start a new history session while retaining the last result as stale."""

        with self._lock:
            if self._last_forecast is not None:
                self._stale_forecast = dict(self._last_forecast)
            self._last_forecast = None
            self._reset_active_state()
            self._last_error = None

    @property
    def source_intervals_completed(self) -> int:
        with self._lock:
            return len(self._activity_frames)

    def ingest_event(self, event: Mapping[str, Any]) -> bool:
        """Consume one real packet event; never retain the packet itself."""

        pending_sequences: list[pd.DataFrame] = []
        with self._lock:
            self._startup_stage_timestamps.setdefault("first_event", datetime.now(timezone.utc).isoformat())
            self._event_count += 1
            try:
                completed = self._flow_builder.feed_event(event)
            except (TypeError, ValueError, FlowBuilderError) as exc:
                reason = str(exc)
                category = "out_of_order" if "chronological" in reason else "invalid_flow_event"
                self._rejected_event_count += 1
                self._rejected_event_categories[category] = self._rejected_event_categories.get(category, 0) + 1
                self._last_rejection_reason = reason
                if isinstance(exc, FlowTableOverflowError):
                    self._last_error = f"flow conversion: {exc}"
                return False
            self._accepted_event_count += 1
            try:
                source_activity = self._source_accumulator.feed(event)
                if source_activity is not None and not source_activity.empty:
                    self._activity_frames.append(source_activity.copy())
            except (TypeError, ValueError) as exc:
                self._last_error = f"source activity: {exc}"
            if int(self._flow_builder.status().get("created_flows", 0)) > 0:
                self._startup_stage_timestamps.setdefault("flow_creation", datetime.now(timezone.utc).isoformat())
            for flow in completed:
                self._completed_flows.append(dict(flow))
                self._completed_flow_count += 1
            if completed:
                self._startup_stage_timestamps.setdefault("flow_closure", datetime.now(timezone.utc).isoformat())
            if completed:
                pending_sequences = self._refresh_states()
            self._refresh_source_outputs()

        for sequence in pending_sequences:
            try:
                result = dict(self._inference_fn(sequence))
            except (OSError, RuntimeError, TypeError, ValueError, KeyError) as exc:
                with self._lock:
                    self._last_error = f"live inference: {exc}"
                continue
            with self._lock:
                self._last_forecast = result
                self._forecast_update_count += 1
                self._startup_stage_timestamps.setdefault("first_inference", datetime.now(timezone.utc).isoformat())
                self._last_error = None
                self._refresh_source_outputs()
        return True

    def _refresh_states(self) -> list[pd.DataFrame]:
        pending_sequences: list[pd.DataFrame] = []
        if not self._completed_flows:
            return pending_sequences
        self._startup_stage_timestamps.setdefault("state_generation", datetime.now(timezone.utc).isoformat())
        try:
            frame = pd.DataFrame(list(self._completed_flows))
            states, _ = build_network_state_for_inference(frame, self.interval_seconds)
        except (TypeError, ValueError, KeyError) as exc:
            self._last_error = f"state generation: {exc}"
            return pending_sequences
        self._startup_stage_timestamps.setdefault("state_validation", datetime.now(timezone.utc).isoformat())

        for row in states.to_dict(orient="records"):
            timestamp = pd.Timestamp(row["timestamp"])
            capture_day = str(row["capture_day"])
            key = (capture_day, timestamp.isoformat())
            if key in self._state_keys:
                continue
            if len(self._state_rows) == self.max_state_records:
                removed = self._state_rows.popleft()
                self._state_keys.discard((str(removed["capture_day"]), pd.Timestamp(removed["timestamp"]).isoformat()))
            self._state_rows.append(dict(row))
            self._state_keys.add(key)
            self._state_count += 1
            self._startup_stage_timestamps.setdefault("first_valid_state", datetime.now(timezone.utc).isoformat())
            if self._latest_state_timestamp is not None and timestamp <= self._latest_state_timestamp:
                continue
            state_frame = pd.DataFrame([row])[STATE_COLUMNS]
            update = self._state_buffer.push(state_frame)
            if update.status == "day_boundary_reset":
                self._buffer_fill = 1
            elif update.status != "waiting_for_next_valid_state":
                self._buffer_fill = min(self.sequence_length, self._buffer_fill + 1)
            self._latest_state_timestamp = timestamp
            if self._buffer_fill >= self.sequence_length:
                self._startup_stage_timestamps.setdefault("buffer_fill", datetime.now(timezone.utc).isoformat())
            if update.sequence is not None:
                pending_sequences.append(update.sequence.copy())
        return pending_sequences

    def _refresh_source_outputs(self) -> None:
        if not self._activity_frames:
            return
        activity = pd.concat(list(self._activity_frames), ignore_index=True)
        try:
            if self._last_forecast is None:
                prioritized = prioritize_sources(activity)
                rows = prioritized.to_dict(orient="records")
            else:
                rows = prioritize_sources_with_forecast(activity, self._last_forecast)
            latest_by_source: dict[str, dict[str, Any]] = {}
            for row in rows:
                source = str(row["source_ip"])
                previous = latest_by_source.get(source)
                if previous is None or str(row.get("interval_end", "")) >= str(previous.get("interval_end", "")):
                    latest_by_source[source] = _json_safe(row)
            priority_order = {"HIGH PRIORITY SOURCE": 0, "MEDIUM PRIORITY SOURCE": 1, "LOW PRIORITY SOURCE": 2}
            self._source_priorities = sorted(
                latest_by_source.values(),
                key=lambda row: (priority_order.get(str(row.get("priority")), 3), -int(row.get("priority_points", 0)), str(row.get("source_ip"))),
            )
            recommendations = recommendations_for_sources(self._source_priorities)
            for recommendation in recommendations:
                recommendation["simulation_only"] = True
            self._mitigation_recommendations = _json_safe(recommendations)
        except (TypeError, ValueError, KeyError) as exc:
            self._last_error = f"source prioritization: {exc}"

    @staticmethod
    def _forecast_payload(result: dict[str, Any], *, status: str, stale: bool) -> dict[str, Any]:
        rows = [dict(row) for row in result.get("forecast", [])]
        scores = [float(row["score"]) for row in rows]
        warnings = [bool(row["warning"]) for row in rows]
        return {
            "status": status,
            "stale": stale,
            "reference_timestamp": result.get("reference_timestamp"),
            "model_version": result.get("model_version"),
            "sequence_length": 10,
            "horizons": _json_safe(rows),
            "forecast_scores": scores,
            "warning_states": warnings,
            "threshold": result.get("threshold"),
            "operating_mode": result.get("operating_mode"),
            "explanation": _json_safe(result.get("explanation", {})),
        }

    def snapshot(self, telemetry: Mapping[str, Any]) -> dict[str, Any]:
        with self._lock:
            status = str(telemetry.get("status", "LIVE_STOPPED"))
            running = status == "LIVE_RUNNING"
            if self._last_forecast is not None:
                forecast_status = "READY" if running else "STALE_NOT_LIVE"
                forecast = self._forecast_payload(self._last_forecast, status=forecast_status, stale=not running)
            else:
                forecast = {
                    "status": "WAITING_FOR_LIVE_HISTORY",
                    "stale": False,
                    "reference_timestamp": None,
                    "model_version": None,
                    "sequence_length": self.sequence_length,
                    "horizons": [],
                    "forecast_scores": [],
                    "warning_states": [],
                    "threshold": None,
                    "operating_mode": None,
                    "explanation": {},
                }
            if self._stale_forecast is not None and self._last_forecast is None:
                forecast["last_forecast"] = self._forecast_payload(
                    self._stale_forecast,
                    status="STALE_NOT_LIVE",
                    stale=True,
                )
            telemetry_payload = _json_safe(dict(telemetry))
            telemetry_payload["flow_count"] = self._completed_flow_count
            last_event_at = telemetry_payload.get("last_event_at")
            if running:
                telemetry_payload["freshness"] = "DATA STALE" if telemetry_payload.get("stale") else "DATA FRESH"
            elif last_event_at:
                telemetry_payload["freshness"] = f"LAST LIVE UPDATE: {last_event_at}"
            else:
                telemetry_payload["freshness"] = "NOT CURRENT"
            valid_events = max(int(telemetry_payload.get("event_count", 0) or 0), self._event_count)
            ignored_events = int(telemetry_payload.get("parse_error_count", 0) or 0)
            packets_seen = valid_events + ignored_events
            telemetry_payload["packet_quality"] = {
                "packets_seen": packets_seen,
                "valid_events": valid_events,
                "ignored_events": ignored_events,
                "dropped_events": int(telemetry_payload.get("dropped_count", 0) or 0),
                "valid_percentage": round((100.0 * valid_events / packets_seen), 2) if packets_seen else 0.0,
                "ignored_percentage": round((100.0 * ignored_events / packets_seen), 2) if packets_seen else 0.0,
                "ignored_categories": telemetry_payload.get("parse_error_categories", {}),
            }
            telemetry_payload["readiness_state"] = self._readiness_state(status, telemetry_payload)
            return {
                "telemetry": telemetry_payload,
                "state": {
                    "valid_state_count": self._state_count,
                    "latest_state_timestamp": self._latest_state_timestamp.isoformat() if self._latest_state_timestamp is not None else None,
                    "buffer_size": self._buffer_fill,
                    "buffer_required": self.sequence_length,
                    "accepted_event_count": self._accepted_event_count,
                    "rejected_event_count": self._rejected_event_count,
                    "rejected_event_categories": dict(self._rejected_event_categories),
                    "last_rejection_reason": self._last_rejection_reason,
                },
                "forecast": forecast,
                "source_priorities": self._source_priorities,
                "mitigation": {
                    "simulation_only": True,
                    "recommendations": self._mitigation_recommendations,
                },
                "last_error": self._last_error,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "forecast_update_count": self._forecast_update_count,
                "startup_timing": self._startup_timing(telemetry_payload),
            }

    def _readiness_state(self, status: str, telemetry: Mapping[str, Any]) -> str:
        if status in {"LIVE_ERROR", "LIVE_UNAVAILABLE", "LIVE_PERMISSION_DENIED"} or self._last_error:
            return "ERROR"
        if status == "LIVE_RUNNING":
            if not self._event_count:
                return "INITIALIZING"
            if not self._completed_flow_count:
                return "CAPTURING"
            if not self._state_count:
                return "BUILDING_FLOW_HISTORY"
            if self._last_forecast is not None:
                return "FORECAST_READY"
            return "BUILDING_NETWORK_HISTORY"
        if status == "LIVE_STOPPED":
            return "STALE" if self._last_forecast is not None or self._stale_forecast is not None else "STOPPED"
        if not telemetry.get("available", True):
            return "ERROR"
        return "STOPPED"

    def _startup_timing(self, telemetry: Mapping[str, Any]) -> dict[str, Any]:
        capture_start = telemetry.get("started_at") or self._session_started_at
        stages: list[dict[str, Any]] = []
        try:
            start = pd.Timestamp(capture_start)
        except (TypeError, ValueError):
            start = pd.Timestamp(self._session_started_at)
        stages.append({"stage": "packet_capture_start", "timestamp": start.isoformat(), "elapsed_seconds": 0.0})
        for stage, timestamp in self._startup_stage_timestamps.items():
            try:
                elapsed = max(0.0, (pd.Timestamp(timestamp) - start).total_seconds())
            except (TypeError, ValueError):
                elapsed = None
            stages.append({"stage": stage, "timestamp": timestamp, "elapsed_seconds": elapsed})
        return {
            "session_started_at": self._session_started_at,
            "stages": stages,
            "flow_stage_note": "flow_creation is the first tracked flow; flow_closure is the first completed flow emitted by the existing timeout/FIN/RST policy",
        }


def _json_safe(value: Any) -> Any:
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.generic):
        return value.item()
    return value
