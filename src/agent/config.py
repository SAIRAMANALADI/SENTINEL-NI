"""File-backed configuration for the Sentinel remote sensor agent."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
import tempfile
from typing import Any
from urllib.parse import urlsplit

from src.agent import __version__


def default_config_path() -> Path:
    return Path.home() / ".sentinel-agent" / "config.json"


@dataclass
class AgentConfig:
    server_url: str = "http://127.0.0.1:8000"
    environment: str = "development"
    interface: str | None = None
    sensor_id: str | None = None
    runtime_token: str | None = field(default=None, repr=False)
    agent_version: str = __version__
    buffer_dir: Path = field(default_factory=lambda: Path.home() / ".sentinel-agent" / "buffer")
    heartbeat_interval_seconds: int = 20
    batch_size: int = 6
    batch_interval_seconds: float = 5.0
    max_buffer_batches: int = 256
    max_buffer_bytes: int = 64 * 1024 * 1024
    retry_base_seconds: float = 1.0
    retry_max_seconds: float = 60.0
    retry_jitter_seconds: float = 0.0
    buffer_overflow_policy: str = "DROP_OLDEST"
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
        config = cls._from_dict(raw)
        config._config_path = config_path
        return config

    @classmethod
    def _from_dict(cls, raw: dict[str, Any]) -> "AgentConfig":
        values = dict(raw)
        for key in ("buffer_dir", "pid_path"):
            if key in values and values[key] is not None:
                values[key] = Path(values[key])
        return cls(**values)

    def save(self, path: str | Path | None = None) -> Path:
        config_path = Path(path or getattr(self, "_config_path", None) or os.getenv("SENTINEL_AGENT_CONFIG") or default_config_path())
        self._config_path = config_path
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
        if self.environment not in {"development", "production"}:
            raise ValueError("environment must be development or production")
        try:
            parsed = urlsplit(self.server_url)
            port = parsed.port
        except ValueError as exc:
            raise ValueError("server_url contains an invalid port") from exc
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("server_url must include an http:// or https:// scheme and host")
        if parsed.username or parsed.password:
            raise ValueError("server_url must not contain embedded credentials")
        if port is not None and not 1 <= port <= 65535:
            raise ValueError("server_url port must be in [1, 65535]")
        if parsed.query or parsed.fragment:
            raise ValueError("server_url must not contain a query or fragment")
        if self.environment == "production" and parsed.scheme != "https":
            raise ValueError("production sensor transport requires an https:// server_url")
        if self.heartbeat_interval_seconds <= 0 or self.batch_size <= 0 or self.batch_interval_seconds <= 0:
            raise ValueError("heartbeat_interval_seconds, batch_size, and batch_interval_seconds must be positive")
        if self.max_buffer_batches <= 0 or self.max_buffer_bytes <= 0:
            raise ValueError("buffer limits must be positive")
        if self.retry_base_seconds <= 0:
            raise ValueError("retry_base_seconds must be positive")
        if self.retry_max_seconds < self.retry_base_seconds:
            raise ValueError("retry_max_seconds must be greater than or equal to retry_base_seconds")
        if self.retry_jitter_seconds < 0:
            raise ValueError("retry_jitter_seconds must not be negative")
        if self.buffer_overflow_policy.upper() not in {"DROP_OLDEST", "REJECT_NEW"}:
            raise ValueError("buffer_overflow_policy must be DROP_OLDEST or REJECT_NEW")
        if isinstance(self.next_sequence, bool) or self.next_sequence < 1:
            raise ValueError("next_sequence must be positive")
        if require_identity and (not self.sensor_id or not self.runtime_token):
            raise ValueError("agent is not registered; run `python -m src.agent register`")
