"""Safe identity helpers for the remote sensor agent."""

from __future__ import annotations

import socket
from copy import copy
from collections.abc import Mapping
from typing import Any

from src.agent.config import AgentConfig, SENSOR_ID_PATTERN


def hostname() -> str:
    return socket.gethostname()


def validate_registration_response(response: Mapping[str, Any]) -> tuple[str, str]:
    """Validate the non-persisted identity returned by central registration."""

    if not isinstance(response, Mapping):
        raise ValueError("registration response must be a JSON object")
    schema_version = response.get("schema_version")
    if schema_version is not None and schema_version != "1":
        raise ValueError("unsupported sensor registration schema version")
    sensor_id = response.get("sensor_id")
    runtime_token = response.get("runtime_token")
    if not isinstance(sensor_id, str) or not SENSOR_ID_PATTERN.fullmatch(sensor_id):
        raise ValueError("registration response contains an invalid sensor_id")
    if not isinstance(runtime_token, str) or not runtime_token.strip():
        raise ValueError("registration response does not contain a runtime_token")
    return sensor_id, runtime_token


def register_config(config: AgentConfig, response: Mapping[str, Any]) -> AgentConfig:
    sensor_id, runtime_token = validate_registration_response(response)
    # Validate the complete candidate before mutating the live configuration.
    candidate = copy(config)
    candidate.sensor_id = sensor_id
    candidate.runtime_token = runtime_token
    candidate.validate(require_identity=True)
    config.sensor_id = sensor_id
    config.runtime_token = runtime_token
    config.validate(require_identity=True)
    return config
