"""Phase F packaging, configuration, diagnostics, and service contracts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.agent.cli import main
from src.agent.config import AgentConfig
from src.agent.diagnostics import collect, validate_config
from src.agent.service import ServiceUnavailable, render_unit, unit_path


def test_saved_runtime_credential_is_separate_and_recoverable(tmp_path: Path) -> None:
    config = AgentConfig(
        server_url="https://central.example",
        interface="Ethernet",
        sensor_id="sensor-0123456789abcdef",
        runtime_token="snr_secret",
        buffer_dir=tmp_path / "buffer",
        pid_path=tmp_path / "agent.pid",
        log_path=tmp_path / "logs" / "agent.log",
    )
    config_path = config.save(tmp_path / "config.json")

    config_payload = json.loads(config_path.read_text(encoding="utf-8"))
    credentials_path = tmp_path / "credentials.json"
    assert config_payload["runtime_token"] is None
    assert "snr_secret" not in config_path.read_text(encoding="utf-8")
    assert json.loads(credentials_path.read_text(encoding="utf-8"))["runtime_token"] == "snr_secret"
    assert AgentConfig.load(config_path).runtime_token == "snr_secret"


def test_config_validation_is_non_network_and_production_fails_closed() -> None:
    config = AgentConfig(server_url="https://central.example", interface="Ethernet")
    assert validate_config(config)["valid"] is True
    with pytest.raises(ValueError, match="requires an https"):
        AgentConfig(server_url="http://central.example", environment="production", interface="Ethernet").validate()


def test_cli_init_validate_and_status_use_installed_contract(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    assert main(["--config", str(config_path), "init", "--server-url", "http://127.0.0.1:8000", "--interface", "test"]) == 0
    assert main(["--config", str(config_path), "config", "validate"]) == 0
    assert main(["--config", str(config_path), "status"]) == 0


def test_diagnostics_redacts_secret_and_reports_capture(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = AgentConfig(
        server_url="https://central.example",
        interface="Ethernet",
        sensor_id="sensor-0123456789abcdef",
        runtime_token="snr_secret",
        buffer_dir=tmp_path / "buffer",
        pid_path=tmp_path / "agent.pid",
    )
    monkeypatch.setattr(
        "src.agent.diagnostics.discover_capture_interfaces",
        lambda: [{"name": "Ethernet", "capture_available": True}],
    )
    result = collect(config, check_connection=False)
    serialized = json.dumps(result)
    assert result["capture"]["status"] == "AVAILABLE"
    assert "snr_secret" not in serialized


def test_linux_service_unit_targets_real_agent_entrypoint() -> None:
    unit = render_unit(Path("/opt/sentinel/config.json"))
    assert "ExecStart=" in unit
    assert "-m src.agent" in unit
    assert "Restart=on-failure" in unit


def test_windows_service_support_is_explicitly_not_claimed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.agent.service.os.name", "nt")
    with pytest.raises(ServiceUnavailable, match="Windows service management is not implemented"):
        unit_path()
