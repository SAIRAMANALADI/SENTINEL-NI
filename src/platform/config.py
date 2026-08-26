"""Central, environment-driven runtime configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value")


def _env_path(name: str, default: Path) -> Path:
    value = os.getenv(name)
    path = Path(value).expanduser() if value else default
    return path if path.is_absolute() else PROJECT_ROOT / path


@dataclass(frozen=True)
class Settings:
    api_host: str
    api_port: int
    model_path: Path
    feature_schema_path: Path
    operating_policy_path: Path
    log_level: str
    telemetry_mode: str
    auth_enabled: bool
    viewer_token: str | None
    operator_token: str | None
    admin_token: str | None
    audit_log_path: Path
    demo_events_path: Path
    telemetry_interface: str | None = None
    telemetry_replay_path: Path | None = None
    telemetry_stale_after_seconds: int = 30
    max_request_bytes: int = 2_000_000

    @classmethod
    def from_env(cls) -> "Settings":
        port_raw = os.getenv("SIH_API_PORT", "8000")
        try:
            port = int(port_raw)
        except ValueError as exc:
            raise ValueError("SIH_API_PORT must be an integer") from exc
        if not 1 <= port <= 65535:
            raise ValueError("SIH_API_PORT must be in [1, 65535]")

        telemetry_mode = os.getenv("SIH_TELEMETRY_MODE", "replay").strip().lower()
        if telemetry_mode not in {"mock", "replay", "live"}:
            raise ValueError("SIH_TELEMETRY_MODE must be mock, replay, or live")

        log_level = os.getenv("SIH_LOG_LEVEL", "INFO").strip().upper()
        if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("SIH_LOG_LEVEL is not a supported logging level")

        auth_enabled = _env_bool("SIH_AUTH_ENABLED", False)
        max_request_bytes_raw = os.getenv("SIH_MAX_REQUEST_BYTES", "2000000")
        try:
            max_request_bytes = int(max_request_bytes_raw)
        except ValueError as exc:
            raise ValueError("SIH_MAX_REQUEST_BYTES must be an integer") from exc
        tokens = {
            "viewer": os.getenv("SIH_VIEWER_TOKEN"),
            "operator": os.getenv("SIH_OPERATOR_TOKEN"),
            "admin": os.getenv("SIH_ADMIN_TOKEN"),
        }
        if auth_enabled and not any(tokens.values()):
            raise ValueError("authentication is enabled but no role token is configured")

        return cls(
            api_host=os.getenv("SIH_API_HOST", "0.0.0.0"),
            api_port=port,
            model_path=_env_path("SIH_MODEL_PATH", PROJECT_ROOT / "models" / "lstm_multistep_k5.pt"),
            feature_schema_path=_env_path(
                "SIH_FEATURE_SCHEMA", PROJECT_ROOT / "configs" / "state_feature_schema.yaml"
            ),
            operating_policy_path=_env_path(
                "SIH_OPERATING_POLICY", PROJECT_ROOT / "configs" / "operating_policy.yaml"
            ),
            log_level=log_level,
            telemetry_mode=telemetry_mode,
            auth_enabled=auth_enabled,
            viewer_token=tokens["viewer"],
            operator_token=tokens["operator"],
            admin_token=tokens["admin"],
            audit_log_path=_env_path(
                "SIH_AUDIT_LOG_PATH", PROJECT_ROOT / "results" / "audit" / "events.jsonl"
            ),
            demo_events_path=_env_path(
                "SIH_DEMO_EVENTS_PATH", PROJECT_ROOT / "data" / "samples" / "final_demo_events.csv"
            ),
            telemetry_interface=os.getenv("SIH_TELEMETRY_INTERFACE") or None,
            telemetry_replay_path=_env_path(
                "SIH_TELEMETRY_REPLAY_PATH", PROJECT_ROOT / "data" / "samples" / "inference_demo_sequence.csv"
            ),
            telemetry_stale_after_seconds=int(os.getenv("SIH_TELEMETRY_STALE_AFTER_SECONDS", "30")),
            max_request_bytes=max_request_bytes,
        )

    def validate(self) -> None:
        for name, path in (
            ("model_path", self.model_path),
            ("feature_schema_path", self.feature_schema_path),
            ("operating_policy_path", self.operating_policy_path),
        ):
            if not path.is_file():
                raise FileNotFoundError(f"{name} does not exist: {path}")
        if self.telemetry_stale_after_seconds <= 0:
            raise ValueError("telemetry_stale_after_seconds must be positive")
        if self.max_request_bytes <= 0:
            raise ValueError("max_request_bytes must be positive")

    def role_tokens(self) -> dict[str, str | None]:
        return {"viewer": self.viewer_token, "operator": self.operator_token, "admin": self.admin_token}
