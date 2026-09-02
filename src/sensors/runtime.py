"""Per-sensor remote state buffering and inference."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from threading import RLock
from typing import Any

import pandas as pd

from src.features.network_state import FEATURE_COLUMNS
from src.forecasting.inference import predict_network_state_sequence
from src.streaming.state_aggregator import STATE_COLUMNS, validate_state
from src.streaming.state_buffer import StateBuffer, StateBufferError


InferenceFunction = Callable[[pd.DataFrame], dict[str, Any]]


class RemoteSensorRuntime:
    """Keep one strict L=10 history and latest forecast for one sensor."""

    def __init__(self, sensor_id: str, *, inference_fn: InferenceFunction = predict_network_state_sequence) -> None:
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

    @staticmethod
    def _state_frame(state: Mapping[str, Any]) -> pd.DataFrame:
        features = state["features"]
        row = {**dict(features), "timestamp": state["timestamp"], "capture_day": state["capture_day"]}
        return validate_state(pd.DataFrame([row])[STATE_COLUMNS])

    def ingest(self, states: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
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
                    self._last_error = "state interval gap; history reset without interpolation"
                elif update.status == "day_boundary_reset":
                    self._history_length = 1
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
        return {
            "sensor_id": self.sensor_id,
            "accepted_states": accepted,
            "forecast_updates": forecast_updates,
            "history_length": self.history_length,
            "forecast_available": self._latest_forecast is not None,
        }

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
                "source_priorities": [],
                "source_status": "UNAVAILABLE_FROM_AGGREGATED_STATE_TELEMETRY",
                "last_error": self._last_error,
            }


class RemoteSensorRuntimeStore:
    """Map sensor IDs to isolated runtime stores."""

    def __init__(self, *, inference_fn: InferenceFunction = predict_network_state_sequence, max_sensors: int = 1024) -> None:
        if max_sensors <= 0:
            raise ValueError("max_sensors must be positive")
        self._runtimes: dict[str, RemoteSensorRuntime] = {}
        self._inference_fn = inference_fn
        self.max_sensors = max_sensors
        self._lock = RLock()

    def _runtime(self, sensor_id: str) -> RemoteSensorRuntime:
        with self._lock:
            runtime = self._runtimes.get(sensor_id)
            if runtime is None:
                if len(self._runtimes) >= self.max_sensors:
                    raise ValueError("maximum remote sensor runtime count reached")
                runtime = RemoteSensorRuntime(sensor_id, inference_fn=self._inference_fn)
                self._runtimes[sensor_id] = runtime
            return runtime

    def ingest(self, sensor_id: str, states: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        return self._runtime(sensor_id).ingest(states)

    def snapshot(self, sensor_id: str) -> dict[str, Any]:
        return self._runtime(sensor_id).snapshot()

    def snapshots(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {sensor_id: runtime.snapshot() for sensor_id, runtime in self._runtimes.items()}
