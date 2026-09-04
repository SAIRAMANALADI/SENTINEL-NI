"""Per-sensor remote state buffering and inference."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from threading import RLock
from typing import Any

import pandas as pd

from src.features.network_state import FEATURE_COLUMNS
from src.forecasting.inference import predict_network_state_sequence
from src.evaluation.mitigation_policy import recommendations_for_sources
from src.streaming.state_aggregator import STATE_COLUMNS, validate_state
from src.streaming.state_buffer import StateBuffer, StateBufferError
from src.streaming.source_activity import SOURCE_ACTIVITY_COLUMNS
from src.streaming.source_forecast import prioritize_sources


InferenceFunction = Callable[[pd.DataFrame], dict[str, Any]]
Clock = Callable[[], datetime]
SOURCE_HISTORY_MAX_ROWS = 512


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RemoteSensorRuntime:
    """Keep one strict L=10 history and latest forecast for one sensor."""

    def __init__(
        self,
        sensor_id: str,
        *,
        inference_fn: InferenceFunction = predict_network_state_sequence,
        source_stale_after_seconds: int = 30,
        clock: Clock = _utc_now,
    ) -> None:
        if source_stale_after_seconds <= 0:
            raise ValueError("source_stale_after_seconds must be positive")
        self.sensor_id = sensor_id
        self._buffer = StateBuffer(sequence_length=10, interval_seconds=10)
        self._inference_fn = inference_fn
        self._lock = RLock()
        self._state_rows: deque[dict[str, Any]] = deque(maxlen=128)
        self._latest_forecast: dict[str, Any] | None = None
        self._accepted_states = 0
        self._history_length = 0
        self._forecast_updates = 0
        self._rejected_states = 0
        self._last_error: str | None = None
        self._last_state_timestamp: str | None = None
        self._source_history: deque[dict[str, Any]] = deque(maxlen=SOURCE_HISTORY_MAX_ROWS)
        self._source_last_received_at: datetime | None = None
        self._source_last_event_timestamp: str | None = None
        self._source_stale_after_seconds = source_stale_after_seconds
        self._clock = clock
        self._source_schema_version: str | None = None
        self._source_priorities: list[dict[str, Any]] = []

    @staticmethod
    def _source_row_json(row: Mapping[str, Any]) -> dict[str, Any]:
        output = dict(row)
        for field in ("interval_start", "interval_end"):
            output[field] = pd.Timestamp(output[field]).isoformat()
        output["capture_day"] = str(output["capture_day"])
        output["source_ip"] = str(output["source_ip"])
        for field in ("flow_count", "packet_count", "unique_destinations", "unique_destination_ports", "syn_count", "ack_count", "rst_count", "priority_points"):
            if field in output:
                output[field] = int(output[field])
        for field in ("byte_count", "mean_packet_size", "mean_iat", "packet_rate", "byte_rate", "flow_growth", "packet_growth", "byte_growth"):
            if field in output:
                output[field] = float(output[field])
        return output

    def _refresh_source_priorities(self) -> None:
        if not self._source_history:
            self._source_priorities = []
            return
        activity = pd.DataFrame(list(self._source_history), columns=SOURCE_ACTIVITY_COLUMNS)
        activity["interval_start"] = pd.to_datetime(activity["interval_start"], utc=True)
        activity["interval_end"] = pd.to_datetime(activity["interval_end"], utc=True)
        prioritized = prioritize_sources(activity, self._latest_forecast)
        if prioritized.empty:
            self._source_priorities = []
            return
        latest_interval = prioritized["interval_start"].max()
        current = prioritized[prioritized["interval_start"] == latest_interval]
        first_seen = activity.groupby("source_ip")["interval_start"].min().to_dict()
        last_seen = activity.groupby("source_ip")["interval_end"].max().to_dict()
        priority_order = {"HIGH PRIORITY SOURCE": 0, "MEDIUM PRIORITY SOURCE": 1, "LOW PRIORITY SOURCE": 2}
        rows: list[dict[str, Any]] = []
        for row in current.to_dict(orient="records"):
            source_ip = str(row["source_ip"])
            record = self._source_row_json(row)
            record["sensor_id"] = self.sensor_id
            record["first_seen"] = pd.Timestamp(first_seen[source_ip]).isoformat()
            record["last_seen"] = pd.Timestamp(last_seen[source_ip]).isoformat()
            record["active"] = True
            record["recent_activity"] = {
                column: record[column]
                for column in SOURCE_ACTIVITY_COLUMNS
                if column not in {"source_ip", "capture_day", "interval_start", "interval_end"}
            }
            rows.append(record)
        self._source_priorities = sorted(
            rows,
            key=lambda row: (
                priority_order.get(str(row.get("priority")), 3),
                -int(row.get("priority_points", 0)),
                -int(row.get("packet_count", 0)),
                str(row.get("source_ip")),
            ),
        )

    def _ingest_source_activity(
        self,
        source_activity: Sequence[Mapping[str, Any]] | None,
        received_at: datetime | None,
    ) -> None:
        if not source_activity:
            return
        for row in source_activity:
            missing = [column for column in SOURCE_ACTIVITY_COLUMNS if column not in row]
            if missing:
                raise ValueError(f"source activity is missing required fields: {missing}")
            self._source_history.append({column: row[column] for column in SOURCE_ACTIVITY_COLUMNS})
        self._source_schema_version = "1"
        self._source_last_received_at = received_at or self._clock()
        self._source_last_event_timestamp = max(
            pd.Timestamp(row["interval_end"]) for row in source_activity
        ).isoformat()
        self._refresh_source_priorities()

    @staticmethod
    def _state_frame(state: Mapping[str, Any]) -> pd.DataFrame:
        features = state["features"]
        row = {**dict(features), "timestamp": state["timestamp"], "capture_day": state["capture_day"]}
        return validate_state(pd.DataFrame([row])[STATE_COLUMNS])

    def ingest(
        self,
        states: Sequence[Mapping[str, Any]],
        source_activity: Sequence[Mapping[str, Any]] | None = None,
        *,
        received_at: datetime | None = None,
    ) -> dict[str, Any]:
        if not states:
            raise ValueError("telemetry batch must contain at least one state")
        forecast_updates = 0
        accepted = 0
        with self._lock:
            for state in states:
                frame = self._state_frame(state)
                timestamp = pd.Timestamp(frame["timestamp"].iloc[0])
                capture_day = str(frame["capture_day"].iloc[0])
                try:
                    update = self._buffer.push(frame)
                except StateBufferError as exc:
                    self._rejected_states += 1
                    self._last_error = str(exc)
                    raise ValueError(f"sensor state rejected: {exc}") from exc
                if update.status == "waiting_for_next_valid_state":
                    # A gap cannot be repaired or interpolated. Reset so a
                    # later contiguous sequence can form without stale state.
                    self._buffer.reset()
                    update = self._buffer.push(frame)
                    self._history_length = 1
                    self._latest_forecast = None
                    self._last_error = "state interval gap; history reset without interpolation"
                elif update.status == "day_boundary_reset":
                    self._history_length = 1
                    self._latest_forecast = None
                else:
                    self._history_length = min(10, self._history_length + 1)
                accepted += 1
                self._accepted_states += 1
                self._last_state_timestamp = timestamp.isoformat()
                self._state_rows.append({**{column: frame[column].iloc[0] for column in FEATURE_COLUMNS}, "timestamp": timestamp.isoformat(), "capture_day": capture_day})
                if update.sequence is not None:
                    result = dict(self._inference_fn(update.sequence))
                    result["sensor_id"] = self.sensor_id
                    self._latest_forecast = result
                    self._forecast_updates += 1
                    forecast_updates += 1
                    self._last_error = None
                    self._refresh_source_priorities()
            self._ingest_source_activity(source_activity, received_at)
        return {
            "sensor_id": self.sensor_id,
            "accepted_states": accepted,
            "forecast_updates": forecast_updates,
            "history_length": self.history_length,
            "forecast_available": self._latest_forecast is not None,
            "source_status": self._source_status(),
            "source_count": len(self._source_priorities),
        }

    def _source_status(self) -> str:
        if not self._source_history:
            return "NO_SOURCE_ATTRIBUTION"
        if not self._source_priorities:
            return "NO_CANDIDATE_SOURCES"
        if self._source_last_received_at is not None:
            age = (self._clock() - self._source_last_received_at).total_seconds()
            if age > self._source_stale_after_seconds:
                return "SOURCE_DATA_STALE"
        return "SOURCE_ATTRIBUTION_AVAILABLE"

    @property
    def history_length(self) -> int:
        return self._history_length

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            forecast = dict(self._latest_forecast) if self._latest_forecast is not None else None
            if forecast is not None:
                forecast["forecast"] = [dict(row) for row in forecast.get("forecast", [])]
            return {
                "sensor_id": self.sensor_id,
                "history_length": min(self.history_length, 10),
                "history_required": 10,
                "state_count": self._accepted_states,
                "forecast_update_count": self._forecast_updates,
                "rejected_state_count": self._rejected_states,
                "latest_state_timestamp": self._last_state_timestamp,
                "forecast_status": "FORECAST_READY" if forecast is not None else "BUILDING_HISTORY",
                "forecast": forecast,
                "source_priorities": [dict(row) for row in self._source_priorities],
                "source_status": self._source_status(),
                "source_attribution": {
                    "schema_version": self._source_schema_version,
                    "status": self._source_status(),
                    "sensor_id": self.sensor_id,
                    "source_count": len(self._source_priorities),
                    "last_event_timestamp": self._source_last_event_timestamp,
                    "last_received_at": self._source_last_received_at.isoformat() if self._source_last_received_at else None,
                    "source_priorities": [dict(row) for row in self._source_priorities],
                },
                "mitigation": {
                    "simulation_only": True,
                    "recommendations": [
                        {**dict(row), "simulation_only": True}
                        for row in recommendations_for_sources(self._source_priorities)
                    ],
                },
                "last_error": self._last_error,
            }


class RemoteSensorRuntimeStore:
    """Map sensor IDs to isolated runtime stores."""

    def __init__(
        self,
        *,
        inference_fn: InferenceFunction = predict_network_state_sequence,
        max_sensors: int = 1024,
        source_stale_after_seconds: int = 30,
        clock: Clock = _utc_now,
    ) -> None:
        if max_sensors <= 0:
            raise ValueError("max_sensors must be positive")
        self._runtimes: dict[str, RemoteSensorRuntime] = {}
        self._inference_fn = inference_fn
        self.max_sensors = max_sensors
        self.source_stale_after_seconds = source_stale_after_seconds
        self.clock = clock
        self._lock = RLock()

    def _runtime(self, sensor_id: str) -> RemoteSensorRuntime:
        with self._lock:
            runtime = self._runtimes.get(sensor_id)
            if runtime is None:
                if len(self._runtimes) >= self.max_sensors:
                    raise ValueError("maximum remote sensor runtime count reached")
                runtime = RemoteSensorRuntime(
                    sensor_id,
                    inference_fn=self._inference_fn,
                    source_stale_after_seconds=self.source_stale_after_seconds,
                    clock=self.clock,
                )
                self._runtimes[sensor_id] = runtime
            return runtime

    def ingest(
        self,
        sensor_id: str,
        states: Sequence[Mapping[str, Any]],
        source_activity: Sequence[Mapping[str, Any]] | None = None,
        *,
        received_at: datetime | None = None,
    ) -> dict[str, Any]:
        return self._runtime(sensor_id).ingest(states, source_activity, received_at=received_at)

    def snapshot(self, sensor_id: str) -> dict[str, Any]:
        return self._runtime(sensor_id).snapshot()

    def snapshots(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {sensor_id: runtime.snapshot() for sensor_id, runtime in self._runtimes.items()}
