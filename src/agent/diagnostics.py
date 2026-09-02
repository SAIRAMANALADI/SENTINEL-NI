"""Operator-safe diagnostics for an installed Sentinel agent."""

from __future__ import annotations

import os
import platform
import sys
from pathlib import Path
from typing import Any

from src.agent import __version__
from src.agent.config import AgentConfig
from src.telemetry.live import LiveTelemetryError, discover_capture_interfaces


def collect(config: AgentConfig, *, check_connection: bool = True) -> dict[str, Any]:
    """Return diagnostics without returning tokens or authorization headers."""

    result: dict[str, Any] = {
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "agent_version": __version__,
        "protocol_version": config.protocol_version,
        "telemetry_schema_version": config.telemetry_schema_version,
        "config_path": str(getattr(config, "_config_path", "")),
        "server_url": config.server_url,
        "https": config.server_url.lower().startswith("https://"),
        "tls": {
            "verification": "required" if config.tls_verify else "disabled_development_only",
            "ca_bundle": str(config.tls_ca_path) if config.tls_ca_path else "system trust store",
            "client_certificate_configured": config.tls_client_cert_path is not None,
            "client_key_configured": config.tls_client_key_path is not None,
        },
        "sensor_id": config.sensor_id,
        "registration": "REGISTERED" if config.sensor_id and config.runtime_token else "NOT_REGISTERED",
        "credential_store": str(config.credentials_path) if config.credentials_path else "not configured",
        "interface": config.interface,
        "capture_backend": config.capture_backend,
        "storage": {
            "buffer_dir": str(config.buffer_dir),
            "log_path": str(config.log_path),
            "buffer_dir_exists": config.buffer_dir.is_dir(),
        },
    }
    try:
        interfaces = discover_capture_interfaces()
        match = next((item for item in interfaces if item["name"] == config.interface), None)
        result["capture"] = {
            "status": "AVAILABLE" if match and match.get("capture_available") else "UNAVAILABLE",
            "interfaces_discovered": len(interfaces),
            "configured_interface_found": match is not None,
            "error": None if match else f"capture interface not found: {config.interface}",
        }
    except (LiveTelemetryError, ImportError, OSError) as exc:
        result["capture"] = {
            "status": "UNAVAILABLE",
            "interfaces_discovered": 0,
            "configured_interface_found": False,
            "error": str(exc),
        }
    if check_connection and config.sensor_id and config.runtime_token:
        try:
            from src.agent.client import SensorClient

            result["connection"] = {"status": "CONNECTED", "central": SensorClient(config).status()}
        except Exception as exc:
            result["connection"] = {"status": "UNREACHABLE", "error": str(exc)[:240]}
    else:
        result["connection"] = {"status": "NOT_CHECKED"}
    return result


def validate_config(config: AgentConfig) -> dict[str, Any]:
    """Validate settings only; never opens capture or contacts the server."""

    config.validate(require_identity=False)
    if not config.interface:
        raise ValueError("interface is required; configure the monitored interface")
    return {"valid": True, "config": config.redacted()}
