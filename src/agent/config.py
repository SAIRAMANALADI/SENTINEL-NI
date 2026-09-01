"""File-backed configuration for the Sentinel remote sensor agent."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from src.agent import __version__


def default_config_path() -> Path:
    return Path.home() / ".sentinel-agent" / "config.json"


@dataclass
class AgentConfig:
    server_url: str = "http://127.0.0.1:8000"
    interface: str | None = None
    sensor_id: str | None = None
    runtime_token: str | None = field(default=None, repr=False)
    agent_version: str = __version__
    buffer_dir: Path = field(default_factory=lambda: Path.home() / ".sentinel-agent" / "buffer")
    heartbeat_interval_seconds: int = 20
    batch_size: int = 6
    max_buffer_batches: int = 256
    max_buffer_bytes: int = 64 * 1024 * 1024
    retry_base_seconds: float = 1.0
    pid_path: Path = field(default_factory=lambda: Path.home() / ".sentinel-agent" / "agent.pid")
    next_sequence: int = 1

    @classmethod
    def load(cls, path: str | Path | None = None) -> "AgentConfig":
        config_path = Path(path or os.getenv("SENTINEL_AGENT_CONFIG") or default_config_path())
        if not config_path.is_file():
            raise FileNotFoundError(f"agent configuration does not exist: {config_path}; run `python -m src.agent init`")
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("agent configuration must be a JSON object")
        return cls._from_dict(raw)

    @classmethod
    def _from_dict(cls, raw: dict[str, Any]) -> "AgentConfig":
        values = dict(raw)
        for key in ("buffer_dir", "pid_path"):
            if key in values and values[key] is not None:
                values[key] = Path(values[key])
        return cls(**values)

    def save(self, path: str | Path | None = None) -> Path:
        config_path = Path(path or os.getenv("SENTINEL_AGENT_CONFIG") or default_config_path())
        config_path.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(self)
        payload["buffer_dir"] = str(self.buffer_dir)
        payload["pid_path"] = str(self.pid_path)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=config_path.parent, prefix=".config-", delete=False) as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            temporary = Path(handle.name)
        temporary.replace(config_path)
        if os.name != "nt":
            config_path.chmod(0o600)
        return config_path

    def redacted(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["buffer_dir"] = str(self.buffer_dir)
        payload["pid_path"] = str(self.pid_path)
        if payload.get("runtime_token"):
            payload["runtime_token"] = "<configured>"
        return payload

    def validate(self, *, require_identity: bool = False) -> None:
        if not self.server_url.startswith(("http://", "https://")):
            raise ValueError("server_url must use http:// or https://")
        if self.heartbeat_interval_seconds <= 0 or self.batch_size <= 0:
            raise ValueError("heartbeat_interval_seconds and batch_size must be positive")
        if self.max_buffer_batches <= 0 or self.max_buffer_bytes <= 0:
            raise ValueError("buffer limits must be positive")
        if self.retry_base_seconds <= 0:
            raise ValueError("retry_base_seconds must be positive")
        if isinstance(self.next_sequence, bool) or self.next_sequence < 1:
            raise ValueError("next_sequence must be positive")
        if require_identity and (not self.sensor_id or not self.runtime_token):
            raise ValueError("agent is not registered; run `python -m src.agent register`")
