"""Remote sensor enrollment, authentication, and telemetry boundary tests."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.features.network_state import FEATURE_COLUMNS
from src.platform.config import Settings


ROOT = Path(__file__).resolve().parents[2]


def _settings(tmp_path: Path, *, rate_limit: int = 60) -> Settings:
    return Settings(
        api_host="127.0.0.1", api_port=8000,
        model_path=ROOT / "models" / "lstm_multistep_k5.pt",
        feature_schema_path=ROOT / "configs" / "state_feature_schema.yaml",
        operating_policy_path=ROOT / "configs" / "operating_policy.yaml",
        log_level="WARNING", telemetry_mode="mock", auth_enabled=True,
        viewer_token="viewer-test", operator_token="operator-test", admin_token="admin-test",
        audit_log_path=tmp_path / "audit.jsonl",
        demo_events_path=ROOT / "data" / "samples" / "final_demo_events.csv",
        sensor_registry_path=tmp_path / "registry.json", sensor_rate_limit_per_minute=rate_limit,
    )


def _state(timestamp: str = "2018-02-22T01:00:00+00:00") -> dict[str, object]:
    return {
        "timestamp": timestamp,
        "capture_day": "2018-02-22",
        "features": {column: 0.0 for column in FEATURE_COLUMNS},
    }


def _register(client: TestClient) -> tuple[str, str]:
    enrollment = client.post(
        "/api/v1/sensors/enrollment", json={"expires_in_seconds": 600},
        headers={"Authorization": "Bearer admin-test"},
    )
    assert enrollment.status_code == 200
    registered = client.post("/api/v1/sensors/register", json={
        "enrollment_token": enrollment.json()["enrollment_token"],
        "hostname": "edge-a", "agent_version": "0.2.0",
    })
    assert registered.status_code == 200
    return registered.json()["sensor_id"], registered.json()["runtime_token"]


def test_enrollment_is_admin_only_and_registration_is_one_time(tmp_path: Path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))
    assert client.post("/api/v1/sensors/enrollment", json={"expires_in_seconds": 600}).status_code == 401
    sensor_id, token = _register(client)
    assert sensor_id.startswith("sensor-")
    replay = client.post("/api/v1/sensors/register", json={
        "enrollment_token": "invalid-enrollment-token-000", "hostname": "edge-b", "agent_version": "0.2.0",
    })
    assert replay.status_code == 401
    assert token.startswith("snr_")


def test_remote_telemetry_requires_sensor_token_and_deduplicates(tmp_path: Path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))
    sensor_id, token = _register(client)
    body = {"schema_version": "1", "sensor_id": sensor_id, "sequence": 1,
            "sent_at": datetime.now(timezone.utc).isoformat(), "states": [_state()]}
    missing = client.post("/api/v1/telemetry", json=body)
    assert missing.status_code == 401
    accepted = client.post("/api/v1/telemetry", json=body, headers={"X-Sentinel-Sensor-Token": token})
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "ACCEPTED"
    duplicate = client.post("/api/v1/telemetry", json=body, headers={"X-Sentinel-Sensor-Token": token})
    assert duplicate.status_code == 200
    assert duplicate.json()["status"] == "DUPLICATE_ACKNOWLEDGED"
    detail = client.get(f"/api/v1/sensors/{sensor_id}", headers={"Authorization": "Bearer viewer-test"})
    assert detail.status_code == 200
    assert detail.json()["runtime"]["state_count"] == 1


def test_remote_telemetry_rejects_cross_interval_batch(tmp_path: Path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))
    sensor_id, token = _register(client)
    body = {"schema_version": "1", "sensor_id": sensor_id, "sequence": 1,
            "sent_at": datetime.now(timezone.utc).isoformat(), "states": [_state(), _state("2018-02-22T01:00:25+00:00")]}
    response = client.post("/api/v1/telemetry", json=body, headers={"X-Sentinel-Sensor-Token": token})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "CONTRACT_ERROR"


def test_remote_telemetry_rejects_wrong_feature_names_as_structured_validation(tmp_path: Path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))
    sensor_id, token = _register(client)
    features = {column: 0.0 for column in FEATURE_COLUMNS}
    features.pop(FEATURE_COLUMNS[0])
    features["unexpected_feature"] = 0.0
    body = {
        "schema_version": "1",
        "sensor_id": sensor_id,
        "sequence": 1,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "states": [{**_state(), "features": features}],
    }
    response = client.post("/api/v1/telemetry", json=body, headers={"X-Sentinel-Sensor-Token": token})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_remote_telemetry_rate_limit_is_checked_before_runtime(tmp_path: Path) -> None:
    client = TestClient(create_app(_settings(tmp_path, rate_limit=1)))
    sensor_id, token = _register(client)
    headers = {"X-Sentinel-Sensor-Token": token}
    body = {"schema_version": "1", "sensor_id": sensor_id, "sequence": 1,
            "sent_at": datetime.now(timezone.utc).isoformat(), "states": [_state()]}
    assert client.post("/api/v1/telemetry", json=body, headers=headers).status_code == 200
    second = {**body, "sequence": 2}
    response = client.post("/api/v1/telemetry", json=second, headers=headers)
    assert response.status_code == 429


def test_remote_telemetry_reaches_the_real_lstm_after_ten_states(tmp_path: Path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))
    sensor_id, token = _register(client)
    states = [(lambda timestamp: _state(timestamp.isoformat()))(datetime(2018, 2, 22, 1, 0, tzinfo=timezone.utc) + timedelta(seconds=index * 10)) for index in range(10)]
    body = {"schema_version": "1", "sensor_id": sensor_id, "sequence": 1,
            "sent_at": datetime.now(timezone.utc).isoformat(), "states": states}
    response = client.post("/api/v1/telemetry", json=body, headers={"X-Sentinel-Sensor-Token": token})
    assert response.status_code == 200
    assert response.json()["forecast"]["forecast_available"] is True
    assert response.json()["forecast"]["forecast_updates"] == 1


def test_remote_telemetry_accepts_optional_source_activity_and_exposes_sensor_scope(tmp_path: Path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))
    sensor_id, token = _register(client)
    source = {
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
    body = {
        "schema_version": "1",
        "source_schema_version": "1",
        "sensor_id": sensor_id,
        "sequence": 1,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "states": [_state()],
        "source_activity": [source],
    }
    response = client.post("/api/v1/telemetry", json=body, headers={"X-Sentinel-Sensor-Token": token})
    assert response.status_code == 200
    assert response.json()["forecast"]["source_status"] == "SOURCE_ATTRIBUTION_AVAILABLE"
    detail = client.get(f"/api/v1/sensors/{sensor_id}", headers={"Authorization": "Bearer viewer-test"}).json()
    runtime = detail["runtime"]
    assert runtime["source_attribution"]["schema_version"] == "1"
    assert runtime["source_priorities"][0]["source_ip"] == "10.0.0.1"
    assert runtime["mitigation"]["simulation_only"] is True


def test_remote_telemetry_rejects_naive_timestamps(tmp_path: Path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))
    sensor_id, token = _register(client)
    body = {
        "schema_version": "1",
        "sensor_id": sensor_id,
        "sequence": 1,
        "sent_at": "2026-09-02T12:00:00",
        "states": [_state("2018-02-22T01:00:00")],
    }
    response = client.post("/api/v1/telemetry", json=body, headers={"X-Sentinel-Sensor-Token": token})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_two_remote_sensors_keep_forecast_histories_isolated(tmp_path: Path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))
    sensor_a, token_a = _register(client)
    sensor_b, token_b = _register(client)
    states = [(lambda timestamp: _state(timestamp.isoformat()))(datetime(2018, 2, 22, 2, 0, tzinfo=timezone.utc) + timedelta(seconds=index * 10)) for index in range(10)]
    for sensor_id, token in ((sensor_a, token_a), (sensor_b, token_b)):
        payload = {"schema_version": "1", "sensor_id": sensor_id, "sequence": 1,
                   "sent_at": datetime.now(timezone.utc).isoformat(), "states": states if sensor_id == sensor_a else states[:1]}
        response = client.post("/api/v1/telemetry", json=payload, headers={"X-Sentinel-Sensor-Token": token})
        assert response.status_code == 200
    details_a = client.get(f"/api/v1/sensors/{sensor_a}", headers={"Authorization": "Bearer viewer-test"}).json()
    details_b = client.get(f"/api/v1/sensors/{sensor_b}", headers={"Authorization": "Bearer viewer-test"}).json()
    assert details_a["runtime"]["state_count"] == 10
    assert details_a["runtime"]["forecast_status"] == "FORECAST_READY"
    assert details_b["runtime"]["state_count"] == 1
    assert details_b["runtime"]["forecast_status"] == "BUILDING_HISTORY"


def test_heartbeat_exposes_independent_agent_and_telemetry_health(tmp_path: Path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))
    sensor_id, token = _register(client)
    response = client.post(
        f"/api/v1/sensors/{sensor_id}/heartbeat",
        json={
            "buffered_item_count": 3, "buffered_bytes": 1200, "capture_status": "RUNNING",
            "last_sent_sequence": 4, "last_acknowledged_sequence": 3,
            "last_state_timestamp": "2018-02-22T01:00:00+00:00", "last_error": "temporary timeout",
            "agent_version": "0.2.1",
        },
        headers={"X-Sentinel-Sensor-Token": token},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["agent_status"] == "ONLINE"
    assert body["telemetry_status"] == "UNKNOWN"
    assert body["capture_status"] == "RUNNING"
    assert body["buffered_item_count"] == 3
    assert body["last_sent_sequence"] == 4
    assert body["health"] == {"agent": "ONLINE", "telemetry": "UNKNOWN", "forecast": "WAITING"}


def test_three_remote_sensors_keep_health_and_state_identity_under_concurrent_ingest(tmp_path: Path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))
    credentials = [_register(client) for _ in range(3)]

    def send(item: tuple[str, str, int]) -> int:
        sensor_id, token, marker = item
        response = client.post(
            "/api/v1/telemetry",
            json={"schema_version": "1", "sensor_id": sensor_id, "sequence": 1,
                  "sent_at": datetime.now(timezone.utc).isoformat(), "states": [_state(), {**_state("2018-02-22T01:00:10+00:00"), "features": {column: float(marker) for column in FEATURE_COLUMNS}}]},
            headers={"X-Sentinel-Sensor-Token": token},
        )
        return response.status_code

    with ThreadPoolExecutor(max_workers=3) as pool:
        assert list(pool.map(send, [(sensor_id, token, marker) for marker, (sensor_id, token) in enumerate(credentials, 1)])) == [200, 200, 200]

    details = [client.get(f"/api/v1/sensors/{sensor_id}", headers={"Authorization": "Bearer viewer-test"}).json() for sensor_id, _ in credentials]
    assert [item["runtime"]["state_count"] for item in details] == [2, 2, 2]
    assert {item["sensor_id"] for item in details} == {sensor_id for sensor_id, _ in credentials}
    assert all(item["runtime"]["sensor_id"] == item["sensor_id"] for item in details)


def test_fleet_endpoint_is_compact_and_reports_actual_counts(tmp_path: Path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))
    for _ in range(5):
        _register(client)
    response = client.get("/api/v1/sensors", headers={"Authorization": "Bearer viewer-test"})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 5
    assert body["health"]["sensor_count"] == 5
    assert body["health"]["forecast_waiting_count"] == 5
    assert all("runtime" not in sensor and sensor["forecast_ready"] is False for sensor in body["sensors"])


def test_sensor_forecast_is_sensor_scoped_and_pending_is_not_an_error(tmp_path: Path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))
    sensor_id, token = _register(client)
    pending = client.get(f"/api/v1/sensors/{sensor_id}/forecast", headers={"Authorization": "Bearer viewer-test"})
    assert pending.status_code == 200
    assert pending.json()["forecast_ready"] is False
    assert pending.json()["forecast"] is None
    assert client.get("/api/v1/sensors/sensor-0000000000000000/forecast", headers={"Authorization": "Bearer viewer-test"}).status_code == 404

    body = {"schema_version": "1", "sensor_id": sensor_id, "sequence": 1,
            "sent_at": datetime.now(timezone.utc).isoformat(), "states": [_state()]}
    assert client.post("/api/v1/telemetry", json=body, headers={"X-Sentinel-Sensor-Token": token}).status_code == 200
    ready = client.get(f"/api/v1/sensors/{sensor_id}/forecast", headers={"Authorization": "Bearer viewer-test"})
    assert ready.status_code == 200
    assert ready.json()["sensor_id"] == sensor_id
    assert ready.json()["forecast_ready"] is False


def test_disabled_sensor_is_not_deleted_and_cannot_send_future_telemetry(tmp_path: Path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))
    sensor_id, token = _register(client)
    disabled = client.post(f"/api/v1/sensors/{sensor_id}/disable", headers={"Authorization": "Bearer operator-test"})
    assert disabled.status_code == 200
    assert disabled.json()["disabled"] is True
    assert disabled.json()["status"] == "OFFLINE"
    assert disabled.json()["registration_state"] == "DISABLED"

    body = {"schema_version": "1", "sensor_id": sensor_id, "sequence": 1,
            "sent_at": datetime.now(timezone.utc).isoformat(), "states": [_state()]}
    rejected = client.post("/api/v1/telemetry", json=body, headers={"X-Sentinel-Sensor-Token": token})
    assert rejected.status_code == 401
    assert "runtime_token" not in disabled.text
