"""Focused Phase B tests for sensor identity and secure registration."""

from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
import yaml

from src.agent.config import AgentConfig
from src.api.app import create_app
from src.platform.config import Settings
from src.sensors.registry import SensorRegistry


ROOT = Path(__file__).resolve().parents[1]


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        api_host="127.0.0.1", api_port=8000,
        model_path=ROOT / "models" / "lstm_multistep_k5.pt",
        feature_schema_path=ROOT / "configs" / "state_feature_schema.yaml",
        operating_policy_path=ROOT / "configs" / "operating_policy.yaml",
        log_level="WARNING", telemetry_mode="mock", auth_enabled=True,
        viewer_token="viewer-test", operator_token="operator-test", admin_token="admin-test",
        audit_log_path=tmp_path / "audit.jsonl",
        demo_events_path=ROOT / "data" / "samples" / "final_demo_events.csv",
        sensor_registry_path=tmp_path / "registry.json",
    )


def _register(client: TestClient, hostname: str = "edge-a") -> tuple[str, str]:
    enrollment = client.post(
        "/api/v1/sensors/enrollment", json={"expires_in_seconds": 600},
        headers={"Authorization": "Bearer admin-test"},
    )
    assert enrollment.status_code == 200
    response = client.post(
        "/api/v1/sensors/register",
        json={
            "enrollment_token": enrollment.json()["enrollment_token"],
            "hostname": hostname,
            "agent_version": "0.2.0",
        },
    )
    assert response.status_code == 200
    return response.json()["sensor_id"], response.json()["runtime_token"]


def test_registry_persists_identity_and_exposes_lifecycle_metadata(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "registry.json"
    first = SensorRegistry(path)
    enrollment = first.create_enrollment()
    registered = first.register(
        enrollment_token=str(enrollment["enrollment_token"]),
        hostname="edge-a",
        agent_version="0.2.0",
    )

    second = SensorRegistry(path)
    record = second.get(registered["sensor_id"])
    assert record["status"] == "REGISTERED"
    assert record["registration_state"] == "REGISTERED"
    assert record["registered_at"] == record["created_at"]
    assert record["last_seen"] is None
    assert record["last_heartbeat"] is None
    assert record["last_telemetry"] is None
    assert record["credential_metadata"] == {"stored": "sha256", "type": "sensor-runtime-token"}
    assert "runtime_token" not in json.dumps(record)
    assert str(registered["runtime_token"]) not in json.dumps(record)


def test_registry_rejects_empty_or_corrupt_storage(tmp_path: Path) -> None:
    empty = tmp_path / "empty.json"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="cannot be read"):
        SensorRegistry(empty)

    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text("{not-json", encoding="utf-8")
    with pytest.raises(ValueError, match="cannot be read"):
        SensorRegistry(corrupt)


def test_registry_lifecycle_requires_fresh_heartbeat_and_telemetry(tmp_path: Path) -> None:
    now = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)
    registry = SensorRegistry(tmp_path / "registry.json", clock=lambda: now)
    enrollment = registry.create_enrollment()
    registered = registry.register(
        enrollment_token=str(enrollment["enrollment_token"]), hostname="edge-a", agent_version="0.2.0"
    )
    sensor_id = registered["sensor_id"]
    assert registry.get(sensor_id)["status"] == "REGISTERED"

    registry.accept_heartbeat(sensor_id, buffered_item_count=0)
    assert registry.get(sensor_id)["status"] == "DEGRADED"
    registry.accept_telemetry(sensor_id, sequence=1, batch_hash="a" * 64, buffered_item_count=0)
    assert registry.get(sensor_id)["status"] == "ONLINE"

    now += timedelta(seconds=91)
    assert registry.get(sensor_id)["status"] == "OFFLINE"


def test_sensor_status_is_sensor_scoped_and_registration_is_not_online(tmp_path: Path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))
    sensor_a, token_a = _register(client, "edge-a")
    sensor_b, token_b = _register(client, "edge-b")

    own = client.get(
        f"/api/v1/sensors/{sensor_a}/status",
        headers={"X-Sentinel-Sensor-Token": token_a},
    )
    assert own.status_code == 200
    assert own.json()["sensor_id"] == sensor_a
    assert own.json()["status"] == "REGISTERED"
    assert "runtime_token" not in own.text

    assert client.get(
        f"/api/v1/sensors/{sensor_b}/status",
        headers={"X-Sentinel-Sensor-Token": token_a},
    ).status_code == 401
    assert client.get(
        "/api/v1/sensors",
        headers={"X-Sentinel-Sensor-Token": token_a},
    ).status_code == 401
    assert client.get(
        "/api/v1/model",
        headers={"X-Sentinel-Sensor-Token": token_a},
    ).status_code == 401
    assert client.post(
        "/api/v1/sensors/enrollment",
        json={"expires_in_seconds": 600},
        headers={"X-Sentinel-Sensor-Token": token_a},
    ).status_code == 401
    assert token_b != token_a


def test_agent_identity_and_production_transport_policy(tmp_path: Path) -> None:
    development = AgentConfig(
        server_url="http://127.0.0.1:8000",
        environment="development",
        buffer_dir=tmp_path / "buffer",
        pid_path=tmp_path / "agent.pid",
    )
    development.validate()

    production = AgentConfig(
        server_url="https://central.example:8443/base",
        environment="production",
        sensor_id="sensor-0123456789abcdef",
        runtime_token="snr_secret",
        buffer_dir=tmp_path / "prod-buffer",
        pid_path=tmp_path / "prod.pid",
    )
    production.validate(require_identity=True)
    saved = production.save(tmp_path / "agent.json")
    loaded = AgentConfig.load(saved)
    assert loaded.sensor_id == production.sensor_id
    assert loaded.environment == "production"
    assert loaded.redacted()["runtime_token"] == "<configured>"
    assert "snr_secret" not in json.dumps(loaded.redacted())

    with pytest.raises(ValueError, match="requires an https"):
        AgentConfig(server_url="http://central.example", environment="production").validate()
    with pytest.raises(ValueError, match="embedded credentials"):
        AgentConfig(server_url="https://user:pass@central.example").validate()
    with pytest.raises(ValueError, match="query or fragment"):
        AgentConfig(server_url="https://central.example/?token=secret").validate()
    with pytest.raises(ValueError, match="scheme and host"):
        AgentConfig(server_url="central.example:8000").validate()


def test_compose_declares_host_backed_registry_mount() -> None:
    compose = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    assert compose["services"]["backend"]["volumes"][-1] == "./results/sensors:/app/results/sensors"
    assert "volumes" not in compose or "sentinel_registry" not in compose["volumes"]


def test_frontend_enrollment_does_not_call_admin_endpoint_or_embed_admin_token() -> None:
    sensor_fleet = (ROOT / "frontend" / "components" / "SensorFleet.tsx").read_text(encoding="utf-8")
    assert "createEnrollment" not in sensor_fleet
    assert "NEXT_PUBLIC_SIH_API_TOKEN" not in sensor_fleet
