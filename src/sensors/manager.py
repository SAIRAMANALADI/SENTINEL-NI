"""Central coordination boundary for sensor registry and runtime state."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from src.sensors.registry import SensorRegistry
from src.sensors.runtime import RemoteSensorRuntimeStore


class SensorManager:
    """Keep fleet orchestration out of FastAPI route handlers.

    The registry owns persistent identity and delivery metadata. The runtime
    store owns process-local L=10 history and the latest computed forecast.
    This class only composes those two sources; it never creates a shared
    state history.
    """

    def __init__(self, registry: SensorRegistry, runtime: RemoteSensorRuntimeStore) -> None:
        self.registry = registry
        self.runtime = runtime

    def _runtime_snapshot(self, sensor_id: str) -> dict[str, Any]:
        return self.runtime.snapshot(sensor_id)

    @staticmethod
    def _warning(snapshot: Mapping[str, Any]) -> bool:
        forecast = snapshot.get("forecast")
        rows = forecast.get("forecast", []) if isinstance(forecast, Mapping) else []
        return bool(rows and rows[0].get("warning"))

    def fleet_summary(self) -> list[dict[str, Any]]:
        """Return compact sensor cards without histories or explanations."""
        summaries: list[dict[str, Any]] = []
        for sensor in self.registry.list():
            snapshot = self._runtime_snapshot(str(sensor["sensor_id"]))
            summaries.append(
                {
                    "sensor_id": sensor["sensor_id"],
                    "hostname": sensor["hostname"],
                    "agent_version": sensor["agent_version"],
                    "status": sensor["status"],
                    "lifecycle_state": sensor.get("registration_state", "REGISTERED"),
                    "disabled": sensor.get("registration_state") == "DISABLED",
                    "last_seen": sensor.get("last_seen"),
                    "last_heartbeat": sensor.get("last_heartbeat"),
                    "last_telemetry": sensor.get("last_telemetry"),
                    "last_telemetry_at": sensor.get("last_telemetry_at"),
                    "source_type": sensor.get("source_type"),
                    "source_status": sensor.get("source_status"),
                    "source_capabilities": sensor.get("source_capabilities"),
                    "last_event": sensor.get("last_event"),
                    "telemetry_freshness_seconds": sensor.get("telemetry_freshness_seconds"),
                    "heartbeat_freshness_seconds": sensor.get("heartbeat_freshness_seconds"),
                    "capture_status": sensor.get("capture_status", "UNKNOWN"),
                    "connection_status": sensor.get("connection_status", "DISCONNECTED"),
                    "buffered_item_count": sensor.get("buffered_item_count", 0),
                    "buffered_bytes": sensor.get("buffered_bytes", 0),
                    "last_sequence": sensor.get("last_sequence", 0),
                    "last_accepted_sequence": sensor.get("last_accepted_sequence", 0),
                    "last_sent_sequence": sensor.get("last_sent_sequence", 0),
                    "agent_status": sensor.get("agent_status", "UNKNOWN"),
                    "telemetry_status": sensor.get("telemetry_status", "UNKNOWN"),
                    "forecast_ready": snapshot.get("forecast_status") == "FORECAST_READY",
                    "latest_warning": self._warning(snapshot),
                    "state_count": snapshot.get("state_count", 0),
                    "history_length": snapshot.get("history_length", 0),
                    "history_required": snapshot.get("history_required", 10),
                    "latest_state_timestamp": snapshot.get("latest_state_timestamp"),
                }
            )
        return summaries

    def fleet_health(self) -> dict[str, int]:
        summaries = self.fleet_summary()
        return {
            "sensor_count": len(summaries),
            "online_sensor_count": sum(item["status"] == "ONLINE" for item in summaries),
            "degraded_sensor_count": sum(item["status"] == "DEGRADED" for item in summaries),
            "offline_sensor_count": sum(item["status"] == "OFFLINE" for item in summaries),
            "active_warning_count": sum(
                item["latest_warning"] and item["status"] in {"ONLINE", "DEGRADED"} for item in summaries
            ),
            "forecast_waiting_count": sum(not item["forecast_ready"] for item in summaries),
        }

    def detail(self, sensor_id: str) -> dict[str, Any]:
        sensor = self.registry.get(sensor_id)
        runtime = self._runtime_snapshot(sensor_id)
        sensor["runtime"] = runtime
        sensor["health"] = {
            "agent": sensor.get("agent_status", "UNKNOWN"),
            "telemetry": sensor.get("telemetry_status", "UNKNOWN"),
            "forecast": "READY" if runtime.get("forecast_status") == "FORECAST_READY" else "WAITING",
        }
        return sensor

    def forecast(self, sensor_id: str) -> dict[str, Any]:
        self.registry.get(sensor_id)
        snapshot = self._runtime_snapshot(sensor_id)
        return {
            "sensor_id": sensor_id,
            "status": snapshot.get("forecast_status", "BUILDING_HISTORY"),
            "forecast_ready": snapshot.get("forecast_status") == "FORECAST_READY",
            "forecast": snapshot.get("forecast"),
        }

    def health(self, sensor_id: str) -> dict[str, Any]:
        sensor = self.registry.get(sensor_id)
        snapshot = self._runtime_snapshot(sensor_id)
        return {
            "sensor_id": sensor_id,
            "status": sensor["status"],
            "registration_state": sensor.get("registration_state", "REGISTERED"),
            "disabled": bool(sensor.get("disabled", False)),
            "health": {
                "agent": sensor.get("agent_status", "UNKNOWN"),
                "telemetry": sensor.get("telemetry_status", "UNKNOWN"),
                "forecast": "READY" if snapshot.get("forecast_status") == "FORECAST_READY" else "WAITING",
            },
            "source_status": snapshot.get("source_status", "NO_SOURCE_ATTRIBUTION"),
            "telemetry_freshness_seconds": sensor.get("telemetry_freshness_seconds"),
            "heartbeat_freshness_seconds": sensor.get("heartbeat_freshness_seconds"),
            "capture_status": sensor.get("capture_status", "UNKNOWN"),
            "connection_status": sensor.get("connection_status", "DISCONNECTED"),
            "last_seen": sensor.get("last_seen"),
            "last_heartbeat": sensor.get("last_heartbeat"),
            "last_telemetry_at": sensor.get("last_telemetry_at"),
        }

    def sources(self, sensor_id: str) -> dict[str, Any]:
        # Keep the manager boundary safe for non-HTTP callers too; otherwise
        # a typo could allocate an unregistered runtime entry.
        self.registry.get(sensor_id)
        snapshot = self._runtime_snapshot(sensor_id)
        rows = [dict(row) for row in snapshot.get("source_priorities", [])]
        return {
            "sensor_id": sensor_id,
            "status": snapshot.get("source_status", "NO_SOURCE_ATTRIBUTION"),
            "source_count": len(rows),
            "source_priorities": rows,
            "source_attribution": dict(snapshot.get("source_attribution", {})),
        }

    def mitigation(self, sensor_id: str) -> dict[str, Any]:
        self.registry.get(sensor_id)
        snapshot = self._runtime_snapshot(sensor_id)
        mitigation = snapshot.get("mitigation", {})
        recommendations = [dict(row) for row in mitigation.get("recommendations", [])]
        return {
            "sensor_id": sensor_id,
            "source_status": snapshot.get("source_status", "NO_SOURCE_ATTRIBUTION"),
            "simulation_only": True,
            "recommendations": recommendations,
        }

    def ingest(
        self,
        sensor_id: str,
        states: Sequence[Mapping[str, Any]],
        source_activity: Sequence[Mapping[str, Any]] | None = None,
        *,
        received_at: Any | None = None,
    ) -> dict[str, Any]:
        return self.runtime.ingest(sensor_id, states, source_activity, received_at=received_at)

    def disable(self, sensor_id: str, *, reason: str | None = None) -> dict[str, Any]:
        self.registry.disable(sensor_id, reason=reason)
        return self.detail(sensor_id)

    def rotate(self, sensor_id: str) -> dict[str, Any]:
        issued = self.registry.rotate(sensor_id)
        detail = self.detail(sensor_id)
        detail["credential_rotation"] = {
            "sensor_id": issued["sensor_id"],
            "rotated_at": issued["rotated_at"],
            "runtime_token": issued["runtime_token"],
        }
        return detail
