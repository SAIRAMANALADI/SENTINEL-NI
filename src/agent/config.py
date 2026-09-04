"""File-backed configuration for the Sentinel remote sensor agent.

The configuration file contains deployment settings only. The runtime token
is kept in a sibling credential file with restrictive permissions where the
operating system supports them. Legacy configurations with an inline token
remain readable so upgrades do not orphan a sensor.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import math
import os
from pathlib import Path
import re
import tempfile
from typing import Any
from urllib.parse import urlsplit

from src.agent import __version__


SENSOR_ID_PATTERN = re.compile(r"^sensor-[a-f0-9]{16}$")


def default_agent_dir() -> Path:
    """Return an OS-appropriate, overridable agent application directory."""

    override = os.getenv("SENTINEL_AGENT_HOME")
    if override:
        return Path(override).expanduser()
    if os.name == "nt":
        base = Path(os.getenv("APPDATA") or (Path.home() / "AppData" / "Roaming"))
        return base / "Sentinel" / "Agent"
    if os.sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Sentinel" / "Agent"
    base = Path(os.getenv("XDG_CONFIG_HOME") or (Path.home() / ".config"))
    return base / "sentinel-agent"


def default_config_path() -> Path:
    return Path(os.getenv("SENTINEL_AGENT_CONFIG") or (default_agent_dir() / "config.json"))


def _restrict_file(path: Path) -> None:
    """Apply owner-only permissions where the platform exposes POSIX modes."""

    try:
        path.chmod(0o600)
    except OSError:
        # Windows ACLs are managed by the host administrator. The limitation is
        # documented; silently claiming vault-grade storage would be worse.
        pass


def _atomic_json_save(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}-", delete=False
    ) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    _restrict_file(temporary)
    temporary.replace(path)
    _restrict_file(path)


@dataclass
class AgentConfig:
    server_url: str = ""
    environment: str = "development"
    interface: str | None = None
    sensor_id: str | None = None
    runtime_token: str | None = field(default=None, repr=False)
    agent_version: str = __version__
    protocol_version: str = "1"
    telemetry_schema_version: str = "1"
    capture_backend: str = "scapy"
    capture_filter: str | None = None
    buffer_dir: Path = field(default_factory=lambda: default_agent_dir() / "buffer")
    heartbeat_interval_seconds: int = 20
    batch_size: int = 6
    batch_interval_seconds: float = 5.0
    max_buffer_batches: int = 256
    max_buffer_bytes: int = 64 * 1024 * 1024
    retry_base_seconds: float = 1.0
    retry_max_seconds: float = 60.0
    retry_jitter_seconds: float = 0.0
    buffer_overflow_policy: str = "DROP_OLDEST"
    log_level: str = "INFO"
    log_path: Path = field(default_factory=lambda: default_agent_dir() / "logs" / "agent.log")
    log_max_bytes: int = 10 * 1024 * 1024
    log_backup_count: int = 5
    connection_timeout_seconds: float = 10.0
    # TLS is explicit so the transport can evolve to mTLS without changing
    # telemetry semantics.  Verification is enabled by default and may only
    # be disabled for explicitly configured development endpoints.
    tls_ca_path: Path | None = field(default=None, repr=False)
    tls_client_cert_path: Path | None = field(default=None, repr=False)
    tls_client_key_path: Path | None = field(default=None, repr=False)
    tls_verify: bool = True
    pid_path: Path = field(default_factory=lambda: default_agent_dir() / "agent.pid")
    credentials_path: Path | None = field(default=None, repr=False)
    next_sequence: int = 1

    @classmethod
    def load(cls, path: str | Path | None = None) -> "AgentConfig":
        config_path = Path(path or default_config_path()).expanduser()
        if not config_path.is_file():
            raise FileNotFoundError(
                f"agent configuration does not exist: {config_path}; run `sentinel-agent init`"
            )
        try:
            raw = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"agent configuration is not valid JSON: {config_path}") from exc
        if not isinstance(raw, dict):
            raise ValueError("agent configuration must be a JSON object")
        config = cls._from_dict(raw)
        config._config_path = config_path
        credential_path = config.credentials_path or (config_path.parent / "credentials.json")
        config.credentials_path = credential_path
        if not config.runtime_token and credential_path.is_file():
            try:
                credentials = json.loads(credential_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise ValueError(f"agent credential store is not valid JSON: {credential_path}") from exc
            if (
                not isinstance(credentials, dict)
                or not isinstance(credentials.get("runtime_token"), str)
                or not credentials["runtime_token"].strip()
            ):
                raise ValueError(f"agent credential store is malformed: {credential_path}")
            config.runtime_token = credentials["runtime_token"]
        return config

    @classmethod
    def _from_dict(cls, raw: dict[str, Any]) -> "AgentConfig":
        values = dict(raw)
        for key in (
            "buffer_dir", "pid_path", "log_path", "credentials_path",
            "tls_ca_path", "tls_client_cert_path", "tls_client_key_path",
        ):
            if key in values and values[key] is not None:
                values[key] = Path(values[key]).expanduser()
        return cls(**values)

    def save(self, path: str | Path | None = None) -> Path:
        config_path = Path(
            path or getattr(self, "_config_path", None) or default_config_path()
        ).expanduser()
        self._config_path = config_path
        credential_path = self.credentials_path or (config_path.parent / "credentials.json")
        self.credentials_path = credential_path
        if self.runtime_token:
            _atomic_json_save(credential_path, {"runtime_token": self.runtime_token})
        else:
            # Do not leave a credential that a later load could silently
            # resurrect after an operator intentionally clears identity.
            credential_path.unlink(missing_ok=True)
        payload = asdict(self)
        for key in (
            "buffer_dir", "pid_path", "log_path", "credentials_path",
            "tls_ca_path", "tls_client_cert_path", "tls_client_key_path",
        ):
            if payload.get(key) is not None:
                payload[key] = str(payload[key])
        # Never put the credential in the ordinary configuration file.
        payload["runtime_token"] = None
        _atomic_json_save(config_path, payload)
        return config_path

    def redacted(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in (
            "buffer_dir", "pid_path", "log_path", "credentials_path",
            "tls_ca_path", "tls_client_cert_path", "tls_client_key_path",
        ):
            if payload.get(key) is not None:
                payload[key] = str(payload[key])
        if payload.get("runtime_token"):
            payload["runtime_token"] = "<configured>"
        return payload

    def validate(self, *, require_identity: bool = False) -> None:
        if self.environment not in {"development", "production"}:
            raise ValueError("environment must be development or production")
        if not isinstance(self.server_url, str) or not self.server_url.strip():
            raise ValueError("server_url is required; run `sentinel-agent init --server-url ...`")
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
        if self.capture_backend != "scapy":
            raise ValueError("capture_backend must be scapy")

        integer_settings = {
            "heartbeat_interval_seconds": self.heartbeat_interval_seconds,
            "batch_size": self.batch_size,
            "max_buffer_batches": self.max_buffer_batches,
            "max_buffer_bytes": self.max_buffer_bytes,
            "log_max_bytes": self.log_max_bytes,
            "log_backup_count": self.log_backup_count,
        }
        for name, value in integer_settings.items():
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{name} must be an integer")
        if isinstance(self.batch_interval_seconds, bool) or not isinstance(self.batch_interval_seconds, (int, float)) or not math.isfinite(self.batch_interval_seconds):
            raise ValueError("batch_interval_seconds must be a finite number")
        if self.heartbeat_interval_seconds <= 0 or self.batch_size <= 0 or self.batch_interval_seconds <= 0:
            raise ValueError("heartbeat_interval_seconds, batch_size, and batch_interval_seconds must be positive")
        if self.max_buffer_batches <= 0 or self.max_buffer_bytes <= 0:
            raise ValueError("buffer limits must be positive")
        for name, value in {
            "retry_base_seconds": self.retry_base_seconds,
            "retry_max_seconds": self.retry_max_seconds,
            "retry_jitter_seconds": self.retry_jitter_seconds,
            "connection_timeout_seconds": self.connection_timeout_seconds,
        }.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{name} must be a finite number")
        if self.retry_base_seconds <= 0:
            raise ValueError("retry_base_seconds must be positive")
        if self.retry_max_seconds < self.retry_base_seconds:
            raise ValueError("retry_max_seconds must be greater than or equal to retry_base_seconds")
        if self.retry_jitter_seconds < 0:
            raise ValueError("retry_jitter_seconds must not be negative")
        if not isinstance(self.buffer_overflow_policy, str) or self.buffer_overflow_policy.upper() not in {"DROP_OLDEST", "REJECT_NEW"}:
            raise ValueError("buffer_overflow_policy must be DROP_OLDEST or REJECT_NEW")
        if self.log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("log_level must be DEBUG, INFO, WARNING, ERROR, or CRITICAL")
        if self.log_max_bytes <= 0 or self.log_backup_count < 0:
            raise ValueError("log_max_bytes must be positive and log_backup_count must not be negative")
        if self.connection_timeout_seconds <= 0:
            raise ValueError("connection_timeout_seconds must be positive")
        if not isinstance(self.tls_verify, bool):
            raise ValueError("tls_verify must be a boolean")
        parsed_scheme = urlsplit(self.server_url).scheme.lower()
        tls_paths = {
            "tls_ca_path": self.tls_ca_path,
            "tls_client_cert_path": self.tls_client_cert_path,
            "tls_client_key_path": self.tls_client_key_path,
        }
        if parsed_scheme != "https" and any(path is not None for path in tls_paths.values()):
            raise ValueError("TLS certificate settings require an https:// server_url")
        if self.tls_ca_path is not None and not self.tls_ca_path.is_file():
            raise ValueError(f"tls_ca_path does not exist: {self.tls_ca_path}")
        if (self.tls_client_cert_path is None) != (self.tls_client_key_path is None):
            raise ValueError("tls_client_cert_path and tls_client_key_path must be configured together")
        for name, path in tls_paths.items():
            if path is not None and not path.is_file():
                raise ValueError(f"{name} does not exist: {path}")
        if self.environment == "production" and not self.tls_verify:
            raise ValueError("production sensor transport requires TLS certificate verification")
        if isinstance(self.next_sequence, bool) or not isinstance(self.next_sequence, int) or self.next_sequence < 1:
            raise ValueError("next_sequence must be positive")
        if self.sensor_id is not None and (
            not isinstance(self.sensor_id, str) or not SENSOR_ID_PATTERN.fullmatch(self.sensor_id)
        ):
            raise ValueError("sensor_id does not match the registered sensor format")
        if self.runtime_token is not None and (
            not isinstance(self.runtime_token, str) or not self.runtime_token.strip()
        ):
            raise ValueError("runtime_token must be a non-empty string when configured")
        if require_identity and (not self.sensor_id or not self.runtime_token):
            raise ValueError("agent is not registered; run `sentinel-agent register`")

    def ensure_writable_storage(self) -> None:
        for directory in (self.buffer_dir, self.pid_path.parent, self.log_path.parent):
            directory.mkdir(parents=True, exist_ok=True)
            probe = directory / ".write-test"
            try:
                probe.write_text("ok", encoding="utf-8")
                probe.unlink(missing_ok=True)
            except OSError as exc:
                raise OSError(f"agent storage is not writable: {directory}") from exc
