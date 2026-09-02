"""End-to-end proof for the real agent-to-central telemetry path."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import socket
import threading
import time
from urllib.request import Request, urlopen

import uvicorn

from src.agent.client import SensorAgent
from src.agent.config import AgentConfig
from src.agent.identity import register_config
from src.agent.client import SensorClient
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


def _state(timestamp: datetime) -> dict[str, object]:
    return {
        "timestamp": timestamp.isoformat(),
        "capture_day": timestamp.date().isoformat(),
        "features": {column: 0.0 for column in FEATURE_COLUMNS},
    }


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _json_request(url: str, *, method: str, payload: dict[str, object], headers: dict[str, str]) -> dict[str, object]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method=method,
    )
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def test_real_agent_posts_to_central_and_reaches_lstm(tmp_path: Path) -> None:
    port = _free_port()
    app = create_app(_settings(tmp_path))
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.05)
        assert server.started is True
        base_url = f"http://127.0.0.1:{port}"
        enrollment = _json_request(
            f"{base_url}/api/v1/sensors/enrollment",
            method="POST",
            payload={"expires_in_seconds": 600},
            headers={"Authorization": "Bearer admin-test"},
        )
        config_path = tmp_path / "agent.json"
        config = AgentConfig(
            server_url=base_url,
            interface="test",
            buffer_dir=tmp_path / "buffer",
            pid_path=tmp_path / "agent.pid",
            batch_size=10,
        )
        config.save(config_path)
        config = AgentConfig.load(config_path)
        registered = SensorClient(config).register(str(enrollment["enrollment_token"]))
        register_config(config, registered)
        config.save(config_path)
        agent = SensorAgent(AgentConfig.load(config_path))
        start = datetime(2018, 2, 22, 1, 0, tzinfo=timezone.utc)
        states = [_state(start + timedelta(seconds=10 * index)) for index in range(10)]
        assert agent.submit_states(states) == "sent"
        status = SensorClient(agent.config).status()
        assert status["runtime"]["forecast_status"] == "FORECAST_READY"
        assert status["runtime"]["state_count"] == 10
        assert status["runtime"]["forecast"]["forecast"]
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        assert not thread.is_alive()


def test_real_agent_buffers_during_network_outage_and_recovers(tmp_path: Path) -> None:
    port = _free_port()
    app = create_app(_settings(tmp_path))
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.05)
        assert server.started is True
        base_url = f"http://127.0.0.1:{port}"
        enrollment = _json_request(
            f"{base_url}/api/v1/sensors/enrollment", method="POST", payload={"expires_in_seconds": 600},
            headers={"Authorization": "Bearer admin-test"},
        )
        config_path = tmp_path / "agent.json"
        config = AgentConfig(server_url=base_url, interface="test", buffer_dir=tmp_path / "buffer", pid_path=tmp_path / "agent.pid", batch_size=10)
        config.save(config_path)
        registered = SensorClient(config).register(str(enrollment["enrollment_token"]))
        register_config(config, registered)
        config.save(config_path)
        agent = SensorAgent(AgentConfig.load(config_path))
        start = datetime(2018, 2, 22, 3, 0, tzinfo=timezone.utc)
        first = [_state(start + timedelta(seconds=10 * index)) for index in range(10)]
        assert agent.submit_states(first) == "sent"

        agent.config.server_url = "http://127.0.0.1:1"
        assert agent.submit_states([_state(start + timedelta(seconds=100))]) == "buffered"
        assert agent.buffer.count == 1

        agent.config.server_url = base_url
        assert agent.flush_buffer() == 1
        assert agent.buffer.count == 0
        status = SensorClient(agent.config).status()
        assert status["last_accepted_sequence"] == 2
        assert status["runtime"]["state_count"] == 11
        assert status["runtime"]["forecast_status"] == "FORECAST_READY"
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        assert not thread.is_alive()
