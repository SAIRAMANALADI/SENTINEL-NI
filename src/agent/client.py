"""Remote sensor client with bounded disk buffering and retry-safe delivery."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import os
from pathlib import Path
import random
import signal
import time
from typing import Any

from src.agent.buffer import BufferFullError, DiskTelemetryBuffer
from src.agent.collector import AgentCollector
from src.agent.config import AgentConfig
from src.agent.identity import hostname
from src.agent.telemetry import TelemetryBatcher
from src.agent.transport import TransportError, request_json
from src.telemetry.live import LiveTelemetryAdapter
from src.platform.logging import get_logger, log_event


LOGGER = get_logger(__name__)
TRANSIENT_HTTP_STATUSES = frozenset({408, 425, 429, 500, 502, 503, 504})


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _is_transient(error: TransportError) -> bool:
    return error.status_code is None or error.status_code in TRANSIENT_HTTP_STATUSES


class SensorClient:
    def __init__(self, config: AgentConfig) -> None:
        self.config = config

    def _url(self, path: str) -> str:
        return f"{self.config.server_url.rstrip('/')}{path}"

    def register(self, enrollment_token: str) -> dict[str, Any]:
        result = request_json(
            self.config.server_url,
            "/api/v1/sensors/register",
            method="POST",
            payload={"enrollment_token": enrollment_token, "hostname": hostname(), "agent_version": self.config.agent_version},
        )
        log_event(LOGGER, "sensor registration succeeded", event_type="registration_succeeded")
        return result

    def heartbeat(self, buffered_item_count: int, **metadata: Any) -> dict[str, Any]:
        self.config.validate(require_identity=True)
        result = request_json(
            self.config.server_url,
            f"/api/v1/sensors/{self.config.sensor_id}/heartbeat",
            method="POST",
            headers={"X-Sentinel-Sensor-Token": self.config.runtime_token or ""},
            payload={"buffered_item_count": buffered_item_count, "agent_version": self.config.agent_version, **metadata},
        )
        log_event(
            LOGGER,
            "sensor heartbeat sent",
            event_type="heartbeat_succeeded",
            sensor_id=self.config.sensor_id,
            buffered_item_count=buffered_item_count,
        )
        return result

    def telemetry(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.config.validate(require_identity=True)
        log_event(
            LOGGER,
            "telemetry send started",
            event_type="telemetry_send_started",
            sensor_id=self.config.sensor_id,
            sequence=payload.get("sequence"),
            state_count=len(payload.get("states", [])),
        )
        result = request_json(
            self.config.server_url,
            "/api/v1/telemetry",
            method="POST",
            headers={"X-Sentinel-Sensor-Token": self.config.runtime_token or ""},
            payload=payload,
        )
        log_event(
            LOGGER,
            "telemetry send succeeded",
            event_type="telemetry_send_succeeded",
            sensor_id=self.config.sensor_id,
            sequence=payload.get("sequence"),
        )
        return result

    def status(self) -> dict[str, Any]:
        self.config.validate(require_identity=True)
        return request_json(
            self.config.server_url,
            f"/api/v1/sensors/{self.config.sensor_id}/status",
            headers={"X-Sentinel-Sensor-Token": self.config.runtime_token or ""},
        )


class SensorAgent:
    def __init__(self, config: AgentConfig) -> None:
        config.validate(require_identity=True)
        if not config.interface:
            raise ValueError("agent interface is required")
        self.config = config
        self.client = SensorClient(config)
        self.buffer = DiskTelemetryBuffer(
            config.buffer_dir,
            max_batches=config.max_buffer_batches,
            max_bytes=config.max_buffer_bytes,
            overflow_policy=config.buffer_overflow_policy,
        )
        self._pending: deque[dict[str, Any]] = deque(maxlen=max(config.batch_size * 4, config.batch_size))
        self._running = False
        self._last_heartbeat = 0.0
        self._collector: AgentCollector | None = None
        self._adapter: LiveTelemetryAdapter | None = None
        self._next_retry_at = 0.0
        self._retry_delay = config.retry_base_seconds
        self._pending_since: float | None = None
        self._capture_status = "STOPPED"
        self._last_heartbeat_at: datetime | None = None
        self._last_telemetry_at: datetime | None = None
        self._last_state_timestamp: str | None = None
        self._last_sent_sequence = 0
        self._last_acknowledged_sequence = 0
        self._last_error: str | None = None
        self._last_error_category: str | None = None
        self._counters = {"states_collected": 0, "batches_sent": 0, "batches_buffered": 0, "retries": 0, "permanent_rejections": 0}
        self._batcher = TelemetryBatcher(
            config.sensor_id or "",
            sequence_start=config.next_sequence,
            batch_size=config.batch_size,
            on_sequence_advanced=self._persist_next_sequence,
        )

    def _persist_next_sequence(self, next_sequence: int) -> None:
        self.config.next_sequence = next_sequence
        self.config.save()

    def _payload(self, states: list[dict[str, Any]]) -> dict[str, Any]:
        payload = self._batcher.build(states)
        log_event(
            LOGGER,
            "telemetry batch created",
            event_type="telemetry_batch_created",
            sensor_id=self.config.sensor_id,
            sequence=payload["sequence"],
            state_count=len(states),
        )
        return payload

    def submit_states(self, states: list[dict[str, Any]]) -> str:
        if not states:
            return "empty"
        payload = self._payload(states)
        try:
            response = self.client.telemetry(payload)
            self._mark_delivery(payload, response)
            self._counters["batches_sent"] += 1
            return "sent"
        except TransportError as exc:
            self._remember_error(exc, "transport")
            log_event(
                LOGGER,
                "telemetry send failed",
                event_type="telemetry_send_failed",
                sensor_id=self.config.sensor_id,
                sequence=payload["sequence"],
                status_code=exc.status_code,
            )
            if not _is_transient(exc):
                self.buffer.reject(payload, reason=str(exc), status_code=exc.status_code)
                self._counters["permanent_rejections"] += 1
                log_event(
                    LOGGER,
                    "telemetry rejected permanently",
                    event_type="telemetry_rejected",
                    sensor_id=self.config.sensor_id,
                    sequence=payload["sequence"],
                    status_code=exc.status_code,
                )
                raise RuntimeError(f"central service rejected telemetry: {exc}") from exc
            try:
                self.buffer.enqueue(payload)
            except BufferFullError:
                log_event(
                    LOGGER,
                    "telemetry buffer full",
                    event_type="telemetry_buffer_full",
                    sensor_id=self.config.sensor_id,
                    sequence=payload["sequence"],
                )
                raise
            log_event(
                LOGGER,
                "telemetry buffered after transient failure",
                event_type="telemetry_buffered",
                sensor_id=self.config.sensor_id,
                sequence=payload["sequence"],
                status_code=exc.status_code,
            )
            self._counters["batches_buffered"] += 1
            return "buffered"

    def flush_buffer(self) -> int:
        if time.monotonic() < self._next_retry_at:
            return 0
        delivered = 0
        while True:
            item = self.buffer.peek()
            if item is None:
                return delivered
            try:
                response = self.client.telemetry(item)
            except TransportError as exc:
                self._remember_error(exc, "transport")
                if not _is_transient(exc):
                    self.buffer.reject(item, reason=str(exc), status_code=exc.status_code)
                    self.buffer.pop(int(item["sequence"]))
                    self._counters["permanent_rejections"] += 1
                    log_event(
                        LOGGER,
                        "buffered telemetry rejected permanently",
                        event_type="telemetry_rejected",
                        sensor_id=self.config.sensor_id,
                        sequence=item["sequence"],
                        status_code=exc.status_code,
                    )
                    continue
                scheduled_delay = min(self._retry_delay, self.config.retry_max_seconds)
                jitter = random.uniform(0.0, self.config.retry_jitter_seconds) if self.config.retry_jitter_seconds else 0.0
                self._next_retry_at = time.monotonic() + scheduled_delay + jitter
                self._retry_delay = min(self._retry_delay * 2, self.config.retry_max_seconds)
                self._counters["retries"] += 1
                log_event(
                    LOGGER,
                    "buffered telemetry retry scheduled",
                    event_type="telemetry_retry",
                    sensor_id=self.config.sensor_id,
                    sequence=item["sequence"],
                    status_code=exc.status_code,
                    retry_delay_seconds=scheduled_delay + jitter,
                )
                return delivered
            self.buffer.pop(int(item["sequence"]))
            self._mark_delivery(item, response)
            self._retry_delay = self.config.retry_base_seconds
            self._next_retry_at = 0.0
            delivered += 1

    def _mark_delivery(self, payload: dict[str, Any], response: dict[str, Any]) -> None:
        now = _utc_now()
        self._last_telemetry_at = now
        self._last_sent_sequence = max(self._last_sent_sequence, int(payload["sequence"]))
        if str(response.get("status", "")).upper() in {"ACCEPTED", "DUPLICATE_ACKNOWLEDGED"}:
            self._last_acknowledged_sequence = max(self._last_acknowledged_sequence, int(payload["sequence"]))
        self._last_error = None
        self._last_error_category = None

    def _remember_error(self, error: Exception, category: str) -> None:
        self._last_error = str(error)[:240]
        self._last_error_category = category

    def _heartbeat(self) -> bool:
        try:
            self.client.heartbeat(
                self.buffer.count,
                buffered_bytes=self.buffer.size_bytes,
                capture_status=self._capture_status,
                last_telemetry_at=self._last_telemetry_at.isoformat() if self._last_telemetry_at else None,
                last_state_timestamp=self._last_state_timestamp,
                last_sent_sequence=self._last_sent_sequence,
                last_acknowledged_sequence=self._last_acknowledged_sequence,
                last_error=self._last_error,
            )
        except TransportError as exc:
            self._remember_error(exc, "heartbeat_transport")
            return False
        except Exception as exc:
            self._remember_error(exc, "heartbeat_error")
            return False
        self._last_heartbeat_at = _utc_now()
        if self._last_error_category and self._last_error_category.startswith("heartbeat"):
            self._last_error = None
            self._last_error_category = None
        return True

    def _on_state(self, state: dict[str, Any]) -> bool:
        if len(self._pending) >= self._pending.maxlen:
            # Keep loss explicit. The main loop will drain; the adapter records rejection.
            return False
        self._pending.append(state)
        self._counters["states_collected"] += 1
        self._last_state_timestamp = str(state.get("timestamp"))
        if self._pending_since is None:
            self._pending_since = time.monotonic()
        return True

    def _drain_pending(self, *, force: bool = False) -> None:
        while self._pending:
            ready_by_size = len(self._pending) >= self.config.batch_size
            ready_by_time = (
                self._pending_since is not None
                and time.monotonic() - self._pending_since >= self.config.batch_interval_seconds
            )
            if not force and not (ready_by_size or ready_by_time):
                return
            count = min(self.config.batch_size, len(self._pending))
            states = [self._pending.popleft() for _ in range(count)]
            try:
                self.submit_states(states)
            except Exception as exc:
                # A permanent rejection is quarantined by submit_states. Keep
                # the capture loop alive and expose the failure in status.
                self._remember_error(exc, "telemetry_delivery_error")
            self._pending_since = time.monotonic() if self._pending else None

    def run(self) -> None:
        self.config.pid_path.parent.mkdir(parents=True, exist_ok=True)
        self.config.pid_path.write_text(str(os.getpid()), encoding="utf-8")
        self._collector = AgentCollector(interface=self.config.interface or "", on_state=self._on_state)
        self._adapter = LiveTelemetryAdapter(
            self.config.interface,
            event_callback=self._collector.ingest_event,
            queue_size=max(1000, self.config.batch_size * 8),
        )
        self._running = True
        try:
            self._capture_status = "STARTING"
            self._adapter.start()
            self._capture_status = "RUNNING"
            self._heartbeat()
            self._last_heartbeat = time.monotonic()
            while self._running:
                self._drain_pending()
                try:
                    self.flush_buffer()
                except Exception as exc:
                    self._remember_error(exc, "flush_error")
                now = time.monotonic()
                if now - self._last_heartbeat >= self.config.heartbeat_interval_seconds:
                    self._heartbeat()
                    self._last_heartbeat = now
                time.sleep(0.25)
        except KeyboardInterrupt:
            pass
        finally:
            self._capture_status = "STOPPING"
            if self._adapter is not None:
                self._adapter.stop()
            if self._collector is not None:
                self._collector.flush()
            self._drain_pending(force=True)
            try:
                self.flush_buffer()
            except Exception as exc:
                self._remember_error(exc, "shutdown_flush_error")
            try:
                self.config.pid_path.unlink()
            except FileNotFoundError:
                pass
            self._running = False
            self._capture_status = "STOPPED"

    def stop(self) -> None:
        self._running = False

    def local_status(self) -> dict[str, Any]:
        now = _utc_now()
        heartbeat_age = (now - self._last_heartbeat_at).total_seconds() if self._last_heartbeat_at else None
        telemetry_age = (now - self._last_telemetry_at).total_seconds() if self._last_telemetry_at else None
        return {
            "sensor_id": self.config.sensor_id or "unknown",
            "hostname": hostname(),
            "agent_version": self.config.agent_version,
            "server_url": self.config.server_url,
            "agent_status": "ONLINE" if self._running else "STOPPED",
            "capture_status": self._capture_status,
            "telemetry_status": "FRESH" if telemetry_age is not None and telemetry_age <= self.config.heartbeat_interval_seconds * 2 else ("STALE" if telemetry_age is not None else "UNKNOWN"),
            "last_heartbeat": self._last_heartbeat_at.isoformat() if self._last_heartbeat_at else None,
            "last_telemetry": self._last_telemetry_at.isoformat() if self._last_telemetry_at else None,
            "last_state_timestamp": self._last_state_timestamp,
            "last_sent_sequence": self._last_sent_sequence,
            "last_acknowledged_sequence": self._last_acknowledged_sequence,
            "last_error": self._last_error,
            "buffer": self.buffer.status,
            "counters": dict(self._counters),
            "config": self.config.redacted(),
        }


def stop_pid(path: str | Path) -> bool:
    pid_path = Path(path)
    if not pid_path.is_file():
        return False
    pid = int(pid_path.read_text(encoding="utf-8").strip())
    os.kill(pid, signal.SIGTERM)
    return True
