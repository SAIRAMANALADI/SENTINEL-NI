"""Safe identity helpers for the remote sensor agent."""

from __future__ import annotations

import socket

from src.agent.config import AgentConfig


def hostname() -> str:
    return socket.gethostname()


def register_config(config: AgentConfig, response: dict[str, str]) -> AgentConfig:
    config.sensor_id = response["sensor_id"]
    config.runtime_token = response["runtime_token"]
    config.validate(require_identity=True)
    return config
