"""Startup and capture checks for the Sentinel agent."""

from __future__ import annotations

from typing import Any

from src.agent.config import AgentConfig
from src.telemetry.live import discover_capture_interfaces


def validate_startup(config: AgentConfig) -> dict[str, Any]:
    """Validate deployment prerequisites before a capture loop is started."""

    config.validate(require_identity=True)
    if not config.interface:
        raise ValueError("interface is required; configure the monitored interface")
    config.ensure_writable_storage()
    interfaces = discover_capture_interfaces()
    matching = next((item for item in interfaces if item["name"] == config.interface), None)
    if matching is None:
        raise RuntimeError(f"capture interface not found: {config.interface}")
    if not matching.get("capture_available", False):
        raise RuntimeError(
            f"capture backend unavailable for interface {config.interface}; install Npcap/libpcap"
        )
    return {
        "capture_backend": config.capture_backend,
        "interface": config.interface,
        "capture_available": True,
        "server_url": config.server_url,
        "https": config.server_url.lower().startswith("https://"),
    }
