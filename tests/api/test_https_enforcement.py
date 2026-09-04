"""Application-level transport policy tests for the central API boundary."""

from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx
import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.features.network_state import FEATURE_COLUMNS
from src.platform.config import Settings
from tests.api.test_security_hardening import _settings


def _production_settings(tmp_path: Path, *, mode: str = "direct_https", proxies: tuple[str, ...] = ()):
    return replace(
        _settings(tmp_path),
        environment="production",
        transport_mode=mode,
        trusted_proxy_cidrs=proxies,
    )


def _async_get(app, *, client: tuple[str, int], headers: dict[str, str]):
    async def request():
        transport = httpx.ASGITransport(app=app, client=client)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http:
            return await http.get("/api/v1/live", headers=headers)

    return asyncio.run(request())


def test_production_rejects_direct_http_and_forged_forwarded_proto(tmp_path: Path) -> None:
    client = TestClient(create_app(_production_settings(tmp_path)), base_url="http://testserver")
    headers = {"Authorization": "Bearer viewer-test"}

    response = client.get("/api/v1/live", headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "HTTPS_REQUIRED"

    forged = client.get("/api/v1/live", headers={**headers, "X-Forwarded-Proto": "https"})
    assert forged.status_code == 403
    assert forged.json()["error"]["code"] == "HTTPS_REQUIRED"


def test_production_https_preserves_authentication_and_internal_health(tmp_path: Path) -> None:
    app = create_app(_production_settings(tmp_path))
    secure = TestClient(app, base_url="https://testserver")

    assert secure.get("/api/v1/live", headers={"Authorization": "Bearer viewer-test"}).status_code == 200
    assert secure.get("/api/v1/live", headers={"Authorization": "Bearer invalid"}).status_code == 401

    internal = httpx.ASGITransport(app=app, client=("127.0.0.1", 8000))

    async def health_request():
        async with httpx.AsyncClient(transport=internal, base_url="http://internal") as http:
            return await http.get("/api/v1/ready")

    assert asyncio.run(health_request()).status_code == 200


def test_trusted_proxy_requires_trusted_client_and_https_forwarded_proto(tmp_path: Path) -> None:
    app = create_app(_production_settings(tmp_path, mode="trusted_proxy", proxies=("127.0.0.1/32",)))
    headers = {"Authorization": "Bearer viewer-test", "X-Forwarded-Proto": "https"}

    trusted = _async_get(app, client=("127.0.0.1", 8443), headers=headers)
    assert trusted.status_code == 200

    untrusted = TestClient(app, base_url="http://testserver").get("/api/v1/live", headers=headers)
    assert untrusted.status_code == 403
    assert untrusted.json()["error"]["code"] == "HTTPS_REQUIRED"

    malformed_chain = _async_get(
        app,
        client=("127.0.0.1", 8443),
        headers={**headers, "X-Forwarded-Proto": "https, http"},
    )
    assert malformed_chain.status_code == 403

    forged_on_secure_scope = TestClient(app, base_url="https://testserver").get(
        "/api/v1/live", headers={**headers, "X-Forwarded-Proto": "https"}
    )
    assert forged_on_secure_scope.status_code == 403


def test_development_http_is_explicitly_allowed(tmp_path: Path) -> None:
    settings = replace(_settings(tmp_path), transport_mode="development_http")
    client = TestClient(create_app(settings), base_url="http://testserver")
    assert client.get("/api/v1/live", headers={"Authorization": "Bearer viewer-test"}).status_code == 200


def test_production_configuration_rejects_development_http(tmp_path: Path) -> None:
    settings = replace(_settings(tmp_path), environment="production", transport_mode="development_http")
    with pytest.raises(ValueError, match="cannot use development_http"):
        settings.validate()


def test_production_environment_defaults_to_direct_https(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIH_ENV", "production")
    monkeypatch.setenv("SIH_AUTH_ENABLED", "true")
    monkeypatch.setenv("SIH_VIEWER_TOKEN", "viewer-test")
    monkeypatch.setenv("SIH_OPERATOR_TOKEN", "operator-test")
    monkeypatch.setenv("SIH_ADMIN_TOKEN", "admin-test")
    monkeypatch.delenv("SIH_TRANSPORT_MODE", raising=False)

    assert Settings.from_env().transport_mode == "direct_https"


def test_https_registration_and_telemetry_remain_authenticated(tmp_path: Path) -> None:
    client = TestClient(create_app(_production_settings(tmp_path)), base_url="https://testserver")
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
            "hostname": "https-edge",
            "agent_version": "0.2.0",
        },
    )
    assert registration.status_code == 200
    sensor_id = registration.json()["sensor_id"]
    telemetry = client.post(
        "/api/v1/telemetry",
        json={
            "schema_version": "1",
            "sensor_id": sensor_id,
            "sequence": 1,
            "sent_at": "2026-09-04T00:00:00+00:00",
            "states": [{
                "timestamp": "2018-02-22T01:00:00+00:00",
                "capture_day": "2018-02-22",
                "features": {column: 0.0 for column in FEATURE_COLUMNS},
            }],
        },
        headers={"X-Sentinel-Sensor-Token": registration.json()["runtime_token"]},
    )
    assert telemetry.status_code == 200
