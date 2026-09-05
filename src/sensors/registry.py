"""Persistent, secret-hashing registry for remote Sentinel sensors."""

from __future__ import annotations

from collections import deque
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import secrets
from threading import RLock
import tempfile
import uuid
from collections.abc import Iterator
from typing import Any, Callable

from src.telemetry.contracts import REMOTE_AGENT_CAPABILITIES, SourceType


class SensorRegistryError(ValueError):
    """Base error for registry contract failures."""


class InvalidEnrollment(SensorRegistryError):
    """Enrollment credential is missing, expired, or already consumed."""


class InvalidSensorCredentials(SensorRegistryError):
    """Sensor token or sensor identity is invalid."""


class SensorNotFound(SensorRegistryError):
    """Requested sensor does not exist."""


class SensorSequenceConflict(SensorRegistryError):
    """A batch sequence conflicts with the accepted sequence history."""


class SensorRateLimitExceeded(SensorRegistryError):
    """A sensor exceeded its bounded request rate."""


class SensorDisabled(InvalidSensorCredentials):
    """A registered sensor was explicitly disabled by an operator."""


REGISTRY_SCHEMA_VERSION = 1


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    return value.astimezone(timezone.utc).isoformat() if value is not None else None


def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _hash_secret(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class SensorRegistry:
    """Store sensor identity and delivery metadata without storing secrets."""

    def __init__(
        self,
        path: str | Path,
        *,
        heartbeat_timeout_seconds: int = 90,
        telemetry_stale_after_seconds: int = 30,
        rate_limit_per_minute: int = 60,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        if heartbeat_timeout_seconds <= 0 or telemetry_stale_after_seconds <= 0:
            raise ValueError("sensor freshness limits must be positive")
        if rate_limit_per_minute <= 0:
            raise ValueError("sensor rate limit must be positive")
        self.path = Path(path)
        self.heartbeat_timeout_seconds = heartbeat_timeout_seconds
        self.telemetry_stale_after_seconds = telemetry_stale_after_seconds
        self.rate_limit_per_minute = rate_limit_per_minute
        self._clock = clock
        self._lock = RLock()
        self._request_times: dict[str, deque[datetime]] = {}
        self._data = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema_version": REGISTRY_SCHEMA_VERSION, "enrollments": {}, "sensors": {}}
        try:
            raw = self.path.read_text(encoding="utf-8")
            if not raw.strip():
                raise ValueError("sensor registry is empty")
            loaded = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"sensor registry cannot be read: {self.path}") from exc
        except ValueError as exc:
            raise ValueError(f"sensor registry cannot be read: {self.path}: {exc}") from exc
        if not isinstance(loaded, dict):
            raise ValueError("sensor registry must be a JSON object")
        version = loaded.get("schema_version", REGISTRY_SCHEMA_VERSION)
        if version != REGISTRY_SCHEMA_VERSION:
            raise ValueError(f"unsupported sensor registry schema version: {version}")
        loaded.setdefault("enrollments", {})
        loaded.setdefault("sensors", {})
        if not isinstance(loaded["enrollments"], dict) or not isinstance(loaded["sensors"], dict):
            raise ValueError("sensor registry collections must be objects")
        for sensor_id, sensor in loaded["sensors"].items():
            if not isinstance(sensor, dict):
                raise ValueError(f"sensor registry record is invalid: {sensor_id}")
            if sensor.get("sensor_id") != sensor_id:
                raise ValueError(f"sensor registry record identity is invalid: {sensor_id}")
            token_hash = sensor.get("runtime_token_hash")
            if (
                not isinstance(token_hash, str)
                or len(token_hash) != 64
                or any(character not in "0123456789abcdef" for character in token_hash)
            ):
                raise ValueError(f"sensor registry credential metadata is invalid: {sensor_id}")
            if not isinstance(sensor.get("credential_metadata", {"type": "sensor-runtime-token", "stored": "sha256"}), dict):
                raise ValueError(f"sensor registry credential metadata is invalid: {sensor_id}")
            sensor.setdefault("registered_at", sensor.get("created_at"))
            sensor.setdefault("last_telemetry", sensor.get("last_telemetry_at"))
            sensor.setdefault("credential_metadata", {"type": "sensor-runtime-token", "stored": "sha256"})
            sensor.setdefault("registration_state", "REGISTERED")
            sensor.setdefault("capture_status", "UNKNOWN")
            sensor.setdefault("connection_status", "DISCONNECTED")
            sensor.setdefault("buffered_bytes", 0)
            sensor.setdefault("last_sent_sequence", 0)
            sensor.setdefault("last_acknowledged_sequence", sensor.get("last_sequence", 0))
            sensor.setdefault("last_state_timestamp", None)
            sensor.setdefault("last_error", None)
            sensor.setdefault("disabled_at", None)
            sensor.setdefault("disabled_reason", None)
            sensor.setdefault("source_type", SourceType.REMOTE_AGENT.value)
            sensor.setdefault("source_status", REMOTE_AGENT_CAPABILITIES.status.value)
            sensor.setdefault("source_capabilities", REMOTE_AGENT_CAPABILITIES.as_dict())
            sensor.setdefault("last_event", sensor.get("last_state_timestamp"))
        loaded["schema_version"] = REGISTRY_SCHEMA_VERSION
        return loaded

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data["schema_version"] = REGISTRY_SCHEMA_VERSION
        payload = json.dumps(self._data, indent=2, sort_keys=True) + "\n"
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=self.path.parent, prefix=".registry-", delete=False
        ) as handle:
            handle.write(payload)
            temporary = Path(handle.name)
        temporary.replace(self.path)

    def create_enrollment(self, *, expires_in_seconds: int = 600) -> dict[str, str | int]:
        if isinstance(expires_in_seconds, bool) or not 60 <= expires_in_seconds <= 86_400:
            raise ValueError("enrollment expiry must be between 60 and 86400 seconds")
        token = secrets.token_urlsafe(32)
        expires_at = self._clock() + timedelta(seconds=expires_in_seconds)
        with self._lock:
            self._purge_enrollments()
            self._data["enrollments"][_hash_secret(token)] = {"expires_at": _iso(expires_at)}
            self._save()
        return {"enrollment_token": token, "expires_at": _iso(expires_at) or "", "expires_in_seconds": expires_in_seconds}

    def register(self, *, enrollment_token: str, hostname: str, agent_version: str) -> dict[str, str]:
        token_hash = _hash_secret(enrollment_token.strip())
        now = self._clock()
        with self._lock:
            self._purge_enrollments()
            enrollment = self._data["enrollments"].pop(token_hash, None)
            if enrollment is None or (_parse(enrollment.get("expires_at")) or now) <= now:
                self._save()
                raise InvalidEnrollment("enrollment credential is invalid or expired")
            sensor_id = f"sensor-{uuid.uuid4().hex[:16]}"
            runtime_token = f"snr_{secrets.token_urlsafe(32)}"
            self._data["sensors"][sensor_id] = {
                "sensor_id": sensor_id,
                "hostname": hostname,
                "agent_version": agent_version,
                "created_at": _iso(now),
                "registered_at": _iso(now),
                "registration_state": "REGISTERED",
                "last_seen": None,
                "last_heartbeat": None,
                "last_telemetry": None,
                "last_telemetry_at": None,
                "last_sequence": 0,
                "last_batch_hash": None,
                "buffered_item_count": 0,
                "buffered_bytes": 0,
                "capture_status": "UNKNOWN",
                "last_sent_sequence": 0,
                "last_acknowledged_sequence": 0,
                "last_state_timestamp": None,
                "source_type": SourceType.REMOTE_AGENT.value,
                "source_status": REMOTE_AGENT_CAPABILITIES.status.value,
                "source_capabilities": REMOTE_AGENT_CAPABILITIES.as_dict(),
                "last_event": None,
                "last_error": None,
                "disabled_at": None,
                "disabled_reason": None,
                "credential_metadata": {"type": "sensor-runtime-token", "stored": "sha256"},
                "runtime_token_hash": _hash_secret(runtime_token),
            }
            self._save()
        return {"sensor_id": sensor_id, "runtime_token": runtime_token, "registered_at": _iso(now) or ""}

    def rotate(self, sensor_id: str) -> dict[str, str]:
        """Issue one replacement runtime credential for an active sensor.

        The old credential is invalid immediately.  The sensor identity and
        all runtime history remain unchanged; operators must deliver the new
        token through their existing secure channel and restart the agent.
        """

        with self._lock:
            sensor = self._sensor(sensor_id)
            if sensor.get("registration_state") == "DISABLED":
                raise SensorDisabled("disabled sensors cannot rotate credentials")
            runtime_token = f"snr_{secrets.token_urlsafe(32)}"
            now = self._clock()
            sensor["runtime_token_hash"] = _hash_secret(runtime_token)
            sensor["credential_metadata"] = {
                "type": "sensor-runtime-token",
                "stored": "sha256",
                "rotated_at": _iso(now),
            }
            self._save()
            return {"sensor_id": sensor_id, "runtime_token": runtime_token, "rotated_at": _iso(now) or ""}

    def _purge_enrollments(self) -> None:
        now = self._clock()
        expired = [
            key for key, record in self._data["enrollments"].items()
            if (_parse(record.get("expires_at")) or now) <= now
        ]
        for key in expired:
            self._data["enrollments"].pop(key, None)

    def _sensor(self, sensor_id: str) -> dict[str, Any]:
        sensor = self._data["sensors"].get(sensor_id)
        if sensor is None:
            raise SensorNotFound("sensor was not found")
        return sensor

    def authenticate(self, sensor_id: str, runtime_token: str | None) -> dict[str, Any]:
        if not runtime_token:
            raise InvalidSensorCredentials("X-Sentinel-Sensor-Token is required")
        with self._lock:
            sensor = self._sensor(sensor_id)
            if sensor.get("registration_state") == "DISABLED":
                raise SensorDisabled("sensor credential is disabled")
            if not secrets.compare_digest(str(sensor["runtime_token_hash"]), _hash_secret(runtime_token)):
                raise InvalidSensorCredentials("sensor credential is invalid")
            return dict(sensor)

    def _check_rate(self, sensor_id: str) -> None:
        now = self._clock()
        history = self._request_times.setdefault(sensor_id, deque())
        cutoff = now - timedelta(minutes=1)
        while history and history[0] < cutoff:
            history.popleft()
        if len(history) >= self.rate_limit_per_minute:
            raise SensorRateLimitExceeded("sensor request rate limit exceeded")
        history.append(now)

    def check_rate(self, sensor_id: str) -> None:
        """Check capacity before expensive runtime processing without consuming a slot."""
        with self._lock:
            self._sensor(sensor_id)
            now = self._clock()
            history = self._request_times.setdefault(sensor_id, deque())
            cutoff = now - timedelta(minutes=1)
            while history and history[0] < cutoff:
                history.popleft()
            if len(history) >= self.rate_limit_per_minute:
                raise SensorRateLimitExceeded("sensor request rate limit exceeded")

    def accept_telemetry(
        self,
        sensor_id: str,
        *,
        sequence: int,
        batch_hash: str,
        buffered_item_count: int,
        last_event: str | None = None,
    ) -> str:
        with self._lock:
            sensor = self._sensor(sensor_id)
            self._check_rate(sensor_id)
            last_sequence = int(sensor.get("last_sequence", 0))
            if sequence == last_sequence and sensor.get("last_batch_hash") == batch_hash:
                return "duplicate"
            if sequence <= last_sequence:
                raise SensorSequenceConflict("telemetry sequence is out of order or conflicts with an accepted batch")
            now = self._clock()
            sensor["last_sequence"] = sequence
            sensor["last_acknowledged_sequence"] = sequence
            sensor["last_batch_hash"] = batch_hash
            sensor["buffered_item_count"] = buffered_item_count
            sensor["last_telemetry"] = _iso(now)
            sensor["last_telemetry_at"] = _iso(now)
            sensor["last_seen"] = _iso(now)
            if last_event is not None:
                sensor["last_event"] = last_event
            sensor["last_error"] = None
            self._save()
            return "accepted"

    def check_telemetry(self, sensor_id: str, *, sequence: int, batch_hash: str) -> str:
        """Check delivery ordering before runtime processing without mutating state."""

        with self._lock:
            sensor = self._sensor(sensor_id)
            last_sequence = int(sensor.get("last_sequence", 0))
            if sequence == last_sequence and sensor.get("last_batch_hash") == batch_hash:
                return "duplicate"
            if sequence <= last_sequence:
                raise SensorSequenceConflict("telemetry sequence is out of order or conflicts with an accepted batch")
            return "accepted"

    @contextmanager
    def telemetry_transaction(self, sensor_id: str) -> Iterator[None]:
        """Serialize telemetry admission, runtime processing, and registry commit."""

        with self._lock:
            self._sensor(sensor_id)
            yield

    def accept_heartbeat(self, sensor_id: str, *, buffered_item_count: int, agent_version: str | None = None) -> None:
        self.accept_heartbeat_details(
            sensor_id,
            buffered_item_count=buffered_item_count,
            agent_version=agent_version,
        )

    def accept_heartbeat_details(
        self,
        sensor_id: str,
        *,
        buffered_item_count: int,
        buffered_bytes: int = 0,
        agent_version: str | None = None,
        capture_status: str = "UNKNOWN",
        last_telemetry_at: datetime | None = None,
        last_state_timestamp: str | None = None,
        last_sent_sequence: int = 0,
        last_acknowledged_sequence: int = 0,
        last_error: str | None = None,
    ) -> None:
        with self._lock:
            sensor = self._sensor(sensor_id)
            self._check_rate(sensor_id)
            now = self._clock()
            sensor["last_heartbeat"] = _iso(now)
            sensor["last_seen"] = _iso(now)
            sensor["buffered_item_count"] = buffered_item_count
            sensor["buffered_bytes"] = buffered_bytes
            sensor["capture_status"] = capture_status[:32]
            sensor["connection_status"] = "CONNECTED"
            sensor["last_state_timestamp"] = last_state_timestamp
            if last_state_timestamp is not None:
                sensor["last_event"] = last_state_timestamp
            sensor["last_sent_sequence"] = max(int(sensor.get("last_sent_sequence", 0)), int(last_sent_sequence), 0)
            sensor["last_acknowledged_sequence"] = max(
                int(sensor.get("last_acknowledged_sequence", sensor.get("last_sequence", 0))),
                int(last_acknowledged_sequence),
                0,
            )
            sensor["last_error"] = last_error[:240] if last_error else None
            if agent_version:
                sensor["agent_version"] = agent_version
            if last_telemetry_at is not None:
                sensor["agent_last_telemetry_at"] = _iso(last_telemetry_at)
            self._save()

    def _public(self, sensor: dict[str, Any]) -> dict[str, Any]:
        now = self._clock()
        heartbeat = _parse(sensor.get("last_heartbeat"))
        telemetry = _parse(sensor.get("last_telemetry_at"))
        last_seen = _parse(sensor.get("last_seen"))
        heartbeat_age = (now - heartbeat).total_seconds() if heartbeat else None
        telemetry_age = (now - telemetry).total_seconds() if telemetry else None
        if sensor.get("registration_state") == "DISABLED":
            status = "OFFLINE"
        elif last_seen is None:
            status = "REGISTERED"
        elif heartbeat_age is None or heartbeat_age > self.heartbeat_timeout_seconds:
            status = "OFFLINE"
        elif heartbeat_age is not None and heartbeat_age <= self.heartbeat_timeout_seconds and telemetry_age is not None and telemetry_age <= self.telemetry_stale_after_seconds:
            status = "ONLINE"
        else:
            status = "DEGRADED"
        return {
            "sensor_id": sensor["sensor_id"],
            "hostname": sensor["hostname"],
            "agent_version": sensor["agent_version"],
            "created_at": sensor["created_at"],
            "registered_at": sensor.get("registered_at", sensor["created_at"]),
            "registration_state": sensor.get("registration_state", "REGISTERED"),
            "disabled": sensor.get("registration_state") == "DISABLED",
            "disabled_at": sensor.get("disabled_at"),
            "disabled_reason": sensor.get("disabled_reason"),
            "last_seen": sensor.get("last_seen"),
            "last_heartbeat": sensor.get("last_heartbeat"),
            "last_telemetry": sensor.get("last_telemetry", sensor.get("last_telemetry_at")),
            "last_telemetry_at": sensor.get("last_telemetry_at"),
            "telemetry_freshness_seconds": telemetry_age,
            "heartbeat_freshness_seconds": heartbeat_age,
            "buffered_item_count": int(sensor.get("buffered_item_count", 0)),
            "buffered_bytes": int(sensor.get("buffered_bytes", 0)),
            "last_sequence": int(sensor.get("last_sequence", 0)),
            "last_accepted_sequence": int(sensor.get("last_acknowledged_sequence", sensor.get("last_sequence", 0))),
            "last_sent_sequence": int(sensor.get("last_sent_sequence", 0)),
            "last_state_timestamp": sensor.get("last_state_timestamp"),
            "source_type": sensor.get("source_type", SourceType.REMOTE_AGENT.value),
            "source_status": sensor.get("source_status", REMOTE_AGENT_CAPABILITIES.status.value),
            "source_capabilities": dict(sensor.get("source_capabilities", REMOTE_AGENT_CAPABILITIES.as_dict())),
            "last_event": sensor.get("last_event", sensor.get("last_state_timestamp")),
            "capture_status": sensor.get("capture_status", "UNKNOWN"),
            "connection_status": sensor.get("connection_status", "DISCONNECTED"),
            "agent_last_telemetry_at": sensor.get("agent_last_telemetry_at"),
            "agent_last_error": sensor.get("last_error"),
            "agent_status": "UNKNOWN" if heartbeat is None else ("ONLINE" if heartbeat_age is not None and heartbeat_age <= self.heartbeat_timeout_seconds else "OFFLINE"),
            "telemetry_status": "UNKNOWN" if telemetry is None else ("FRESH" if telemetry_age is not None and telemetry_age <= self.telemetry_stale_after_seconds else "STALE"),
            "credential_metadata": dict(sensor.get("credential_metadata", {"type": "sensor-runtime-token", "stored": "sha256"})),
            "status": status,
        }

    def get(self, sensor_id: str) -> dict[str, Any]:
        with self._lock:
            return self._public(self._sensor(sensor_id))

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            return [self._public(sensor) for sensor in self._data["sensors"].values()]

    def disable(self, sensor_id: str, *, reason: str | None = None) -> None:
        """Revoke future sensor authentication without deleting its record."""
        with self._lock:
            sensor = self._sensor(sensor_id)
            sensor["registration_state"] = "DISABLED"
            sensor["disabled_at"] = _iso(self._clock())
            sensor["disabled_reason"] = reason[:240] if reason else "disabled by operator"
            self._save()
