"""Frontend-facing, sensor-scoped read contracts."""

from __future__ import annotations

from datetime import datetime, timezone
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


def _register(client: TestClient) -> tuple[str, str]:
    enrollment = client.post(
        "/api/v1/sensors/enrollment",
        json={"expires_in_seconds": 600},
        headers={"Authorization": "Bearer admin-test"},
    )
    assert enrollment.status_code == 200
    registered = client.post(
        "/api/v1/sensors/register",
        json={
            "enrollment_token": enrollment.json()["enrollment_token"],
            "hostname": "edge-a",
            "agent_version": "0.2.0",
        },
    )
    assert registered.status_code == 200
    return registered.json()["sensor_id"], registered.json()["runtime_token"]


def _telemetry(sensor_id: str) -> dict[str, object]:
    return {
        "schema_version": "1",
        "source_schema_version": "1",
        "sensor_id": sensor_id,
        "sequence": 1,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "states": [
            {
                "timestamp": "2018-02-22T01:00:00+00:00",
                "capture_day": "2018-02-22",
                "features": {column: 0.0 for column in FEATURE_COLUMNS},
            }
        ],
        "source_activity": [
            {
                "source_ip": "10.0.0.1",
                "capture_day": "2018-02-22",
                "interval_start": "2018-02-22T01:00:00+00:00",
                "interval_end": "2018-02-22T01:00:10+00:00",
                "flow_count": 2,
                "packet_count": 10,
                "byte_count": 10000,
                "unique_destinations": 3,
                "unique_destination_ports": 3,
                "mean_packet_size": 1000,
                "mean_iat": 1,
                "syn_count": 0,
                "ack_count": 10,
                "rst_count": 0,
                "packet_rate": 1,
                "byte_rate": 1000,
            }
        ],
    }


def test_sensor_read_contracts_are_viewer_scoped_and_pending_safe(tmp_path: Path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))
    sensor_id, sensor_token = _register(client)
    viewer = {"Authorization": "Bearer viewer-test"}

    assert client.get(f"/api/v1/sensors/{sensor_id}/health").status_code == 401
    health = client.get(f"/api/v1/sensors/{sensor_id}/health", headers=viewer)
    assert health.status_code == 200
    assert health.json()["sensor_id"] == sensor_id
    assert health.json()["health"]["forecast"] == "WAITING"

    sources = client.get(f"/api/v1/sensors/{sensor_id}/sources", headers=viewer)
    assert sources.status_code == 200
    assert sources.json()["status"] == "NO_SOURCE_ATTRIBUTION"
    assert sources.json()["source_count"] == 0

    mitigation = client.get(f"/api/v1/sensors/{sensor_id}/mitigation", headers=viewer)
    assert mitigation.status_code == 200
    assert mitigation.json() == {
        "sensor_id": sensor_id,
        "source_status": "NO_SOURCE_ATTRIBUTION",
        "simulation_only": True,
        "recommendations": [],
    }

    telemetry = client.post(
        "/api/v1/telemetry",
        json=_telemetry(sensor_id),
        headers={"X-Sentinel-Sensor-Token": sensor_token},
    )
    assert telemetry.status_code == 200

    sources = client.get(f"/api/v1/sensors/{sensor_id}/sources", headers=viewer)
    assert sources.status_code == 200
    assert sources.json()["status"] == "SOURCE_ATTRIBUTION_AVAILABLE"
    assert sources.json()["source_priorities"][0]["source_ip"] == "10.0.0.1"
    assert sources.json()["source_attribution"]["sensor_id"] == sensor_id

    mitigation = client.get(f"/api/v1/sensors/{sensor_id}/mitigation", headers=viewer)
    assert mitigation.status_code == 200
    assert mitigation.json()["simulation_only"] is True
    assert mitigation.json()["recommendations"][0]["automatic_block"] is False


def test_sensor_read_contracts_do_not_cross_sensor_boundaries(tmp_path: Path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))
    sensor_a, token_a = _register(client)
    sensor_b, _ = _register(client)

    accepted = client.post(
        "/api/v1/telemetry",
        json=_telemetry(sensor_a),
        headers={"X-Sentinel-Sensor-Token": token_a},
    )
    assert accepted.status_code == 200

    viewer = {"Authorization": "Bearer viewer-test"}
    b_sources = client.get(f"/api/v1/sensors/{sensor_b}/sources", headers=viewer)
    b_mitigation = client.get(f"/api/v1/sensors/{sensor_b}/mitigation", headers=viewer)
    assert b_sources.status_code == 200
    assert b_sources.json()["source_count"] == 0
    assert b_mitigation.status_code == 200
    assert b_mitigation.json()["recommendations"] == []

    for suffix in ("health", "forecast", "sources", "mitigation"):
        missing = client.get(
            f"/api/v1/sensors/sensor-0000000000000000/{suffix}",
            headers=viewer,
        )
        assert missing.status_code == 404
