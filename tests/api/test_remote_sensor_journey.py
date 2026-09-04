"""Focused acceptance journey for one remote sensor and the central API."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.features.network_state import FEATURE_COLUMNS
from src.platform.config import Settings


ROOT = Path(__file__).resolve().parents[2]


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        api_host="127.0.0.1",
        api_port=8000,
        model_path=ROOT / "models" / "lstm_multistep_k5.pt",
        feature_schema_path=ROOT / "configs" / "state_feature_schema.yaml",
        operating_policy_path=ROOT / "configs" / "operating_policy.yaml",
        log_level="WARNING",
        telemetry_mode="mock",
        auth_enabled=True,
        viewer_token="viewer-test",
        operator_token="operator-test",
        admin_token="admin-test",
        audit_log_path=tmp_path / "audit.jsonl",
        demo_events_path=ROOT / "data" / "samples" / "final_demo_events.csv",
        sensor_registry_path=tmp_path / "registry.json",
    )


def _state(timestamp: datetime) -> dict[str, object]:
    return {
        "timestamp": timestamp.isoformat(),
        "capture_day": timestamp.date().isoformat(),
        "features": {column: 0.0 for column in FEATURE_COLUMNS},
    }


def test_remote_sensor_journey_heartbeat_telemetry_forecast_and_dashboard_contract(tmp_path: Path) -> None:
    """Registration alone is not online; accepted telemetry completes the path to K=5 output."""

    client = TestClient(create_app(_settings(tmp_path)))
    enrollment = client.post(
        "/api/v1/sensors/enrollment",
        json={"expires_in_seconds": 600},
        headers={"Authorization": "Bearer admin-test"},
    )
    assert enrollment.status_code == 200
    registration = client.post(
        "/api/v1/sensors/register",
        json={
            "enrollment_token": enrollment.json()["enrollment_token"],
            "hostname": "remote-journey-a",
            "agent_version": "0.2.0",
        },
    )
    assert registration.status_code == 200
    sensor_id = registration.json()["sensor_id"]
    sensor_token = registration.json()["runtime_token"]
    sensor_headers = {"X-Sentinel-Sensor-Token": sensor_token}
    viewer_headers = {"Authorization": "Bearer viewer-test"}

    heartbeat = client.post(
        f"/api/v1/sensors/{sensor_id}/heartbeat",
        json={"capture_status": "RUNNING", "agent_version": "0.2.0"},
        headers=sensor_headers,
    )
    assert heartbeat.status_code == 200
    assert heartbeat.json()["status"] == "DEGRADED"
    assert heartbeat.json()["health"] == {
        "agent": "ONLINE",
        "telemetry": "UNKNOWN",
        "forecast": "WAITING",
    }

    start = datetime(2018, 2, 22, 4, 0, tzinfo=timezone.utc)
    telemetry = client.post(
        "/api/v1/telemetry",
        json={
            "schema_version": "1",
            "sensor_id": sensor_id,
            "sequence": 1,
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "states": [_state(start + timedelta(seconds=index * 10)) for index in range(10)],
        },
        headers=sensor_headers,
    )
    assert telemetry.status_code == 200
    assert telemetry.json()["status"] == "ACCEPTED"
    assert telemetry.json()["forecast"]["forecast_available"] is True
    assert telemetry.json()["forecast"]["forecast_updates"] == 1

    fleet = client.get("/api/v1/sensors", headers=viewer_headers)
    assert fleet.status_code == 200
    summary = next(sensor for sensor in fleet.json()["sensors"] if sensor["sensor_id"] == sensor_id)
    assert summary["status"] == "ONLINE"
    assert summary["telemetry_status"] == "FRESH"
    assert summary["forecast_ready"] is True
    assert fleet.json()["health"]["online_sensor_count"] == 1

    detail = client.get(f"/api/v1/sensors/{sensor_id}", headers=viewer_headers)
    assert detail.status_code == 200
    assert detail.json()["runtime"]["sensor_id"] == sensor_id
    assert detail.json()["runtime"]["forecast_status"] == "FORECAST_READY"
    assert len(detail.json()["runtime"]["forecast"]["forecast"]) == 5
