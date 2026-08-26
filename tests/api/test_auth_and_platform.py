"""Authentication, authorization, telemetry, audit, and configuration tests."""

from pathlib import Path

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.api.models import PacketEvent
from src.platform.audit import AuditLogger
from src.platform.config import Settings
from src.platform.metrics import MetricsRegistry
from src.telemetry.mock import MockTelemetryAdapter
from src.telemetry.replay import ReplayTelemetryAdapter


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
    )


def test_role_authorization_boundary(tmp_path: Path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))
    assert client.get("/api/v1/model").status_code == 401
    assert client.get("/api/v1/model", headers={"Authorization": "Bearer viewer-test"}).status_code == 200
    assert client.post(
        "/api/v1/mitigation",
        headers={"Authorization": "Bearer viewer-test"},
        json={"sources": [{"source_ip": "10.0.0.2", "priority": "LOW PRIORITY SOURCE", "priority_points": 0}]},
    ).status_code == 403
    assert client.post(
        "/api/v1/mitigation",
        headers={"Authorization": "Bearer operator-test"},
        json={"sources": [{"source_ip": "10.0.0.2", "priority": "LOW PRIORITY SOURCE", "priority_points": 0}]},
    ).status_code == 200
    assert client.get("/api/v1/security-contract", headers={"Authorization": "Bearer operator-test"}).status_code == 403
    assert client.get("/api/v1/security-contract", headers={"Authorization": "Bearer admin-test"}).status_code == 200


def test_mock_and_replay_adapters(tmp_path: Path) -> None:
    adapter = MockTelemetryAdapter([{"id": 1}])
    assert adapter.read_event() is None
    adapter.start()
    assert adapter.read_event() == {"id": 1}
    assert adapter.read_event() is None
    adapter.stop()
    assert adapter.status()["started"] is False

    replay = ReplayTelemetryAdapter(ROOT / "data" / "samples" / "inference_demo_sequence.csv")
    replay.start()
    event = replay.read_event()
    assert event is not None
    assert replay.status()["adapter"] == "replay"
    replay.stop()


def test_application_lifespan_stops_telemetry(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    adapter = MockTelemetryAdapter([{"id": 1}])
    adapter.start()
    app.state.runtime.telemetry = adapter

    with TestClient(app) as client:
        assert client.get("/api/v1/health").status_code == 200
        assert adapter.status()["started"] is True

    assert adapter.status()["started"] is False


def test_audit_and_metrics_are_safe(tmp_path: Path) -> None:
    path = tmp_path / "audit" / "events.jsonl"
    record = AuditLogger(path).record(
        event_type="mitigation",
        model_version="model-v1",
        policy_version="policy-v1",
        candidate_source="10.0.0.2",
        mitigation_recommendation="Monitor source",
    )
    assert record["simulation_only"] is True
    assert '"simulation_only": true' in path.read_text(encoding="utf-8")

    metrics = MetricsRegistry()
    metrics.increment("request_count")
    metrics.observe("inference_latency", 12.5)
    assert metrics.snapshot()["counters"]["request_count"] == 1
    assert metrics.snapshot()["latencies"]["inference_latency"]["last_ms"] == 12.5


def test_metrics_latency_storage_is_constant_size() -> None:
    metrics = MetricsRegistry()
    for value in range(10_000):
        metrics.observe("request_latency", float(value))

    snapshot = metrics.snapshot()["latencies"]["request_latency"]
    assert snapshot["count"] == 10_000
    assert snapshot["last_ms"] == 9_999.0
    assert snapshot["mean_ms"] == 4_999.5
    assert set(metrics._latencies["request_latency"]) == {"count", "total_ms", "last_ms"}
