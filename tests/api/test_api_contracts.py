"""API contract, readiness, and recommendation integration tests."""

from __future__ import annotations

from datetime import datetime, timedelta
from dataclasses import replace
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient

from app import streamlit_app
from src.api.app import create_app
from src.platform.config import Settings
from src.features.network_state import FEATURE_COLUMNS


ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "data" / "samples" / "inference_demo_sequence.csv"


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


def _forecast_payload() -> dict[str, object]:
    frame = pd.read_csv(SAMPLE)
    rows = []
    start = datetime(2018, 2, 22, 1, 0, 0)
    for index, row in frame.iterrows():
        rows.append(
            {
                "timestamp": (start + timedelta(seconds=10 * index)).isoformat(),
                "capture_day": "2018-02-22",
                "features": {column: float(row[column]) for column in FEATURE_COLUMNS},
            }
        )
    return {"sequence": rows}


def _packet_event(source_ip: str = "10.0.0.2") -> dict[str, object]:
    return {
        "timestamp": "2018-02-22T01:00:00",
        "source_ip": source_ip,
        "destination_ip": "10.0.0.20",
        "source_port": 12345,
        "destination_port": 443,
        "protocol": "TCP",
        "packet_length": 100.0,
        "tcp_flags": "SYN",
    }


def test_health_ready_model_and_forecast_contract(tmp_path: Path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))
    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    ready = client.get("/api/v1/ready")
    assert ready.status_code == 200
    assert ready.json()["ready"] is True

    model = client.get("/api/v1/model")
    assert model.status_code == 200
    assert model.json()["feature_count"] == 17
    assert model.json()["score_name"] == "Forecast Score"

    forecast = client.post("/api/v1/forecast", json=_forecast_payload())
    assert forecast.status_code == 200
    body = forecast.json()
    assert len(body["forecast"]) == 5
    assert body["service_state"] == "HEALTHY"
    assert "model_checkpoint" not in body


def test_oversized_request_is_rejected_before_body_validation(tmp_path: Path) -> None:
    settings = replace(_settings(tmp_path), max_request_bytes=100)
    client = TestClient(create_app(settings))

    response = client.post(
        "/api/v1/source-priority",
        content=b"x" * 101,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"
    assert response.json()["error"]["max_request_bytes"] == 100


def test_telemetry_status_and_live_control_boundary(tmp_path: Path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))
    telemetry = client.get("/api/v1/telemetry")
    assert telemetry.status_code == 200
    assert telemetry.json()["mode"] == "mock"
    assert telemetry.json()["status"] == "STOPPED"
    start = client.post("/api/v1/telemetry/start")
    assert start.status_code == 409
    assert start.json()["error"]["code"] == "LIVE_MODE_REQUIRED"


def test_live_telemetry_without_interface_is_reported_not_started(tmp_path: Path) -> None:
    settings = replace(_settings(tmp_path), telemetry_mode="live")
    client = TestClient(create_app(settings))
    telemetry = client.get("/api/v1/telemetry")
    assert telemetry.status_code == 200
    assert telemetry.json()["status"] == "LIVE_UNAVAILABLE"
    assert telemetry.json()["service_state"] == "TELEMETRY_UNAVAILABLE"
    start = client.post("/api/v1/telemetry/start")
    assert start.status_code == 503
    assert start.json()["error"]["code"] == "CAPTURE_UNAVAILABLE"


def test_source_priority_and_mitigation_reuse_existing_policy(tmp_path: Path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))
    source = client.post(
        "/api/v1/source-priority",
        json={"events": [_packet_event(), {**_packet_event(), "timestamp": "2018-02-22T01:00:01"}], "network_warning": True},
    )
    assert source.status_code == 200
    sources = source.json()["source_priorities"]
    assert len(sources) == 1

    mitigation = client.post(
        "/api/v1/mitigation",
        json={"sources": [{"source_ip": "10.0.0.2", "priority": "HIGH PRIORITY SOURCE", "priority_points": 5}]},
    )
    assert mitigation.status_code == 200
    assert mitigation.json()["simulation_only"] is True
    assert mitigation.json()["recommendations"][0]["automatic_block"] is False


def test_demo_endpoint_composes_real_integrated_engine(tmp_path: Path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))
    demo = client.post("/api/v1/demo")
    assert demo.status_code == 200
    body = demo.json()
    assert [row["horizon_seconds"] for row in body["network_forecast"]["forecasts"]] == [10, 20, 30, 40, 50]
    assert body["simulation_only"] is True
    assert len(body["source_priorities"]) == 3


def test_invalid_payloads_are_structured(tmp_path: Path) -> None:
    client = TestClient(create_app(_settings(tmp_path)))
    missing_sequence = client.post("/api/v1/forecast", json={})
    assert missing_sequence.status_code == 422
    assert missing_sequence.json()["error"]["code"] == "VALIDATION_ERROR"

    invalid_packet = client.post("/api/v1/source-priority", json={"events": [{**_packet_event(), "source_ip": "not-an-ip"}]})
    assert invalid_packet.status_code == 422
    assert invalid_packet.json()["error"]["code"] == "VALIDATION_ERROR"

    wrong_features = _forecast_payload()
    wrong_features["sequence"][0]["features"].pop(FEATURE_COLUMNS[0])  # type: ignore[index]
    wrong_features["sequence"][0]["features"]["extra"] = 1.0  # type: ignore[index]
    invalid_features = client.post("/api/v1/forecast", json=wrong_features)
    assert invalid_features.status_code == 422
    assert invalid_features.json()["error"]["code"] == "CONTRACT_ERROR"

    invalid_port = client.post(
        "/api/v1/source-priority",
        json={"events": [{**_packet_event(), "source_port": 65536}]},
    )
    assert invalid_port.status_code == 422

    nonfinite_length = client.post(
        "/api/v1/source-priority",
        json={"events": [{**_packet_event(), "packet_length": "NaN"}]},
    )
    assert nonfinite_length.status_code == 422


def test_readiness_is_false_when_model_is_unavailable(tmp_path: Path) -> None:
    settings = replace(_settings(tmp_path), model_path=tmp_path / "missing-model.pt")
    client = TestClient(create_app(settings))
    ready = client.get("/api/v1/ready")
    assert ready.status_code == 503
    assert ready.json()["ready"] is False
    assert ready.json()["service_state"] == "MODEL_UNAVAILABLE"


def test_dashboard_integrated_mode_calls_backend() -> None:
    source = Path(streamlit_app.__file__).read_text(encoding="utf-8")
    assert 'post_json("/api/v1/demo")' in source
    assert "run_final_demo(" not in source
