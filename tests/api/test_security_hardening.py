"""Central security boundary, credential lifecycle, and isolation tests."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.features.network_state import FEATURE_COLUMNS
from src.platform.config import Settings


ROOT = Path(__file__).resolve().parents[2]


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


def _register(client: TestClient, hostname: str) -> tuple[str, str]:
    enrollment = client.post(
        "/api/v1/sensors/enrollment", json={"expires_in_seconds": 600},
        headers={"Authorization": "Bearer admin-test", "X-Request-ID": "enroll-request"},
    )
    assert enrollment.status_code == 200
    response = client.post("/api/v1/sensors/register", json={
        "enrollment_token": enrollment.json()["enrollment_token"],
        "hostname": hostname, "agent_version": "0.2.0",
    })
    assert response.status_code == 200
    return response.json()["sensor_id"], response.json()["runtime_token"]


def _state(timestamp: str = "2018-02-22T01:00:00+00:00") -> dict[str, object]:
    return {
        "timestamp": timestamp,
        "capture_day": "2018-02-22",
        "features": {column: 0.0 for column in FEATURE_COLUMNS},
    }


def _telemetry(sensor_id: str, sequence: int = 1) -> dict[str, object]:
    return {
        "schema_version": "1",
        "sensor_id": sensor_id,
        "sequence": sequence,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "states": [_state()],
    }


def test_rotation_is_admin_only_replaces_old_token_and_preserves_identity(tmp_path: Path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))
    sensor_id, old_token = _register(client, "edge-a")
    forbidden = client.post(
        f"/api/v1/sensors/{sensor_id}/rotate-credential",
        headers={"Authorization": "Bearer operator-test"},
    )
    assert forbidden.status_code == 403

    rotated = client.post(
        f"/api/v1/sensors/{sensor_id}/rotate-credential",
        headers={"Authorization": "Bearer admin-test", "X-Request-ID": "rotate-request"},
    )
    assert rotated.status_code == 200
    new_token = rotated.json()["credential_rotation"]["runtime_token"]
    assert new_token != old_token
    assert rotated.json()["sensor_id"] == sensor_id
    assert old_token not in rotated.text

    assert client.post("/api/v1/telemetry", json=_telemetry(sensor_id), headers={
        "X-Sentinel-Sensor-Token": old_token,
    }).status_code == 401
    accepted = client.post("/api/v1/telemetry", json=_telemetry(sensor_id), headers={
        "X-Sentinel-Sensor-Token": new_token,
    })
    assert accepted.status_code == 200

    audit = (tmp_path / "audit.jsonl").read_text(encoding="utf-8")
    assert "sensor_credential_rotated" in audit
    assert old_token not in audit and new_token not in audit
    assert "rotate-request" in audit


def test_sensor_credential_cannot_impersonate_another_sensor_or_poison_its_runtime(tmp_path: Path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))
    sensor_a, token_a = _register(client, "edge-a")
    sensor_b, token_b = _register(client, "edge-b")
    spoof = client.post("/api/v1/telemetry", json=_telemetry(sensor_b), headers={
        "X-Sentinel-Sensor-Token": token_a,
    })
    assert spoof.status_code == 401
    assert client.get(f"/api/v1/sensors/{sensor_b}/status", headers={
        "X-Sentinel-Sensor-Token": token_a,
    }).status_code == 401
    assert client.post("/api/v1/sensors/enrollment", json={"expires_in_seconds": 600}, headers={
        "X-Sentinel-Sensor-Token": token_a,
    }).status_code == 401
    assert client.post("/api/v1/telemetry", json=_telemetry(sensor_b), headers={
        "X-Sentinel-Sensor-Token": token_b,
    }).status_code == 200
    b_detail = client.get(f"/api/v1/sensors/{sensor_b}", headers={
        "Authorization": "Bearer viewer-test",
    }).json()
    assert b_detail["runtime"]["state_count"] == 1
    assert sensor_a != sensor_b


def test_disabled_sensor_rejects_heartbeat_and_other_sensor_continues(tmp_path: Path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))
    sensor_a, token_a = _register(client, "edge-a")
    sensor_b, token_b = _register(client, "edge-b")
    assert client.post(f"/api/v1/sensors/{sensor_a}/disable", headers={
        "Authorization": "Bearer operator-test",
    }).status_code == 200
    heartbeat = client.post(f"/api/v1/sensors/{sensor_a}/heartbeat", json={
        "buffered_item_count": 0,
    }, headers={"X-Sentinel-Sensor-Token": token_a})
    assert heartbeat.status_code == 401
    assert client.post("/api/v1/telemetry", json=_telemetry(sensor_b), headers={
        "X-Sentinel-Sensor-Token": token_b,
    }).status_code == 200


def test_security_headers_are_present_and_hsts_is_https_only(tmp_path: Path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert "Strict-Transport-Security" not in response.headers
    secure_client = TestClient(create_app(_settings(tmp_path / "secure")), base_url="https://testserver")
    secure_response = secure_client.get("/api/v1/health")
    assert secure_response.headers["Strict-Transport-Security"].startswith("max-age=31536000")


def test_role_tokens_cannot_be_used_as_sensor_credentials(tmp_path: Path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))
    sensor_id, _ = _register(client, "edge-a")
    response = client.post("/api/v1/telemetry", json=_telemetry(sensor_id), headers={
        "X-Sentinel-Sensor-Token": "admin-test",
    })
    assert response.status_code == 401


def test_oversized_request_is_rejected_before_endpoint_processing(tmp_path: Path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))
    response = client.post(
        "/api/v1/telemetry",
        content=b"{}",
        headers={"Content-Length": "2000001"},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"
