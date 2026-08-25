"""API contract tests for the read-only live runtime endpoint."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from src.api.app import create_app
from src.platform.config import Settings


ROOT = Path(__file__).resolve().parents[1]


def _settings(tmp_path: Path, *, auth_enabled: bool = False) -> Settings:
    return Settings(
        api_host="127.0.0.1",
        api_port=8000,
        model_path=ROOT / "models" / "lstm_multistep_k5.pt",
        feature_schema_path=ROOT / "configs" / "state_feature_schema.yaml",
        operating_policy_path=ROOT / "configs" / "operating_policy.yaml",
        log_level="WARNING",
        telemetry_mode="mock",
        auth_enabled=auth_enabled,
        viewer_token="viewer-test" if auth_enabled else None,
        operator_token="operator-test" if auth_enabled else None,
        admin_token="admin-test" if auth_enabled else None,
        audit_log_path=tmp_path / "audit.jsonl",
        demo_events_path=ROOT / "data" / "samples" / "final_demo_events.csv",
    )


def test_live_endpoint_is_read_only_and_returns_waiting_contract(tmp_path: Path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))
    response = client.get("/api/v1/live")

    assert response.status_code == 200
    body = response.json()
    assert set(body) >= {"telemetry", "state", "forecast", "source_priorities", "mitigation"}
    assert body["forecast"]["status"] == "WAITING_FOR_LIVE_HISTORY"
    assert body["forecast"]["horizons"] == []
    assert body["state"]["buffer_required"] == 10
    assert body["mitigation"]["simulation_only"] is True


def test_live_endpoint_requires_viewer_when_auth_enabled(tmp_path: Path) -> None:
    client = TestClient(create_app(_settings(tmp_path, auth_enabled=True)))
    assert client.get("/api/v1/live").status_code == 401
    assert client.get("/api/v1/live", headers={"Authorization": "Bearer viewer-test"}).status_code == 200

