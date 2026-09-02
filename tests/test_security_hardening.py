"""Agent-side transport and secret-handling security contracts."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from src.agent.config import AgentConfig
from src.agent.diagnostics import collect
from src.agent.transport import build_tls_context, request_json


def test_tls_context_defaults_to_chain_and_hostname_verification() -> None:
    context = build_tls_context()
    assert context.verify_mode.name == "CERT_REQUIRED"
    assert context.check_hostname is True


def test_insecure_tls_context_is_explicit_development_only() -> None:
    context = build_tls_context(verify_tls=False)
    assert context.verify_mode.name == "CERT_NONE"
    assert context.check_hostname is False


def test_transport_passes_https_context_without_exposing_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    response = Mock()
    response.read.return_value = b'{"status":"ok"}'
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    observed: dict[str, object] = {}

    def fake_urlopen(request: object, *, timeout: float, context: object) -> Mock:
        observed.update(timeout=timeout, context=context, url=getattr(request, "full_url", ""))
        return response

    monkeypatch.setattr("src.agent.transport.urlopen", fake_urlopen)
    result = request_json("https://central.example", "/health", timeout=3.5)
    assert result == {"status": "ok"}
    assert observed["timeout"] == 3.5
    assert observed["context"] is not None
    assert "token" not in str(observed["url"]).lower()


def test_production_rejects_insecure_transport_and_invalid_tls_paths(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="certificate verification"):
        AgentConfig(
            server_url="https://central.example",
            environment="production",
            tls_verify=False,
        ).validate()
    with pytest.raises(ValueError, match="does not exist"):
        AgentConfig(
            server_url="https://central.example",
            tls_ca_path=tmp_path / "missing-ca.pem",
        ).validate()
    with pytest.raises(ValueError, match="configured together"):
        AgentConfig(
            server_url="https://central.example",
            tls_client_cert_path=tmp_path / "cert.pem",
        ).validate()


def test_diagnostics_reports_tls_state_but_never_secret(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = AgentConfig(
        server_url="https://central.example",
        sensor_id="sensor-0123456789abcdef",
        runtime_token="snr_super-secret",
        interface="Ethernet",
        buffer_dir=tmp_path / "buffer",
    )
    monkeypatch.setattr(
        "src.agent.diagnostics.discover_capture_interfaces",
        lambda: [{"name": "Ethernet", "capture_available": True}],
    )
    result = collect(config, check_connection=False)
    assert result["tls"]["verification"] == "required"
    assert "snr_super-secret" not in json.dumps(result)
