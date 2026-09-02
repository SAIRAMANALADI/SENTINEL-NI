"""Remote sensor client with bounded disk buffering and retry-safe delivery."""

from __future__ import annotations

from collections import deque
import json
import os
from pathlib import Path
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

    def heartbeat(self, buffered_item_count: int) -> dict[str, Any]:
        self.config.validate(require_identity=True)
        result = request_json(
            self.config.server_url,
            f"/api/v1/sensors/{self.config.sensor_id}/heartbeat",
            method="POST",
            headers={"X-Sentinel-Sensor-Token": self.config.runtime_token or ""},
            payload={"buffered_item_count": buffered_item_count, "agent_version": self.config.agent_version},
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
        )
        self._pending: deque[dict[str, Any]] = deque(maxlen=max(config.batch_size * 4, config.batch_size))
        self._running = False
        self._last_heartbeat = 0.0
        self._collector: AgentCollector | None = None
        self._adapter: LiveTelemetryAdapter | None = None
        self._next_retry_at = 0.0
        self._retry_delay = config.retry_base_seconds
        self._pending_since: float | None = None
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
            self.client.telemetry(payload)
            return "sent"
        except TransportError as exc:
            log_event(
                LOGGER,
                "telemetry send failed",
                event_type="telemetry_send_failed",
                sensor_id=self.config.sensor_id,
                sequence=payload["sequence"],
                status_code=exc.status_code,
            )
            if exc.status_code is not None and exc.status_code not in {408, 425, 429, 500, 502, 503, 504}:
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
                self.client.telemetry(item)
            except TransportError as exc:
                if exc.status_code is not None and exc.status_code not in {408, 425, 429, 500, 502, 503, 504}:
                    log_event(
                        LOGGER,
                        "buffered telemetry rejected permanently",
                        event_type="telemetry_rejected",
                        sensor_id=self.config.sensor_id,
                        sequence=item["sequence"],
                        status_code=exc.status_code,
                    )
                    raise RuntimeError(f"central service rejected buffered telemetry: {exc}") from exc
                self._next_retry_at = time.monotonic() + self._retry_delay
                self._retry_delay = min(self._retry_delay * 2, 60.0)
                log_event(
                    LOGGER,
                    "buffered telemetry retry scheduled",
                    event_type="telemetry_retry",
                    sensor_id=self.config.sensor_id,
                    sequence=item["sequence"],
                    status_code=exc.status_code,
                    retry_delay_seconds=self._retry_delay,
                )
                return delivered
            self.buffer.pop(int(item["sequence"]))
            self._retry_delay = self.config.retry_base_seconds
            self._next_retry_at = 0.0
            delivered += 1

    def _on_state(self, state: dict[str, Any]) -> bool:
        if len(self._pending) >= self._pending.maxlen:
            # Keep loss explicit. The main loop will drain; the adapter records rejection.
            return False
        self._pending.append(state)
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
            self.submit_states(states)
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
            self._adapter.start()
            self.client.heartbeat(self.buffer.count)
            self._last_heartbeat = time.monotonic()
            while self._running:
                self._drain_pending()
                self.flush_buffer()
                now = time.monotonic()
                if now - self._last_heartbeat >= self.config.heartbeat_interval_seconds:
                    self.client.heartbeat(self.buffer.count)
                    self._last_heartbeat = now
                time.sleep(0.25)
        except KeyboardInterrupt:
            pass
        finally:
            if self._adapter is not None:
                self._adapter.stop()
            if self._collector is not None:
                self._collector.flush()
            self._drain_pending(force=True)
            self.flush_buffer()
            try:
                self.config.pid_path.unlink()
            except FileNotFoundError:
                pass
            self._running = False

    def stop(self) -> None:
        self._running = False

    def local_status(self) -> dict[str, Any]:
        return {"config": self.config.redacted(), "buffered_batches": self.buffer.count, "buffered_bytes": self.buffer.size_bytes}


def stop_pid(path: str | Path) -> bool:
    pid_path = Path(path)
    if not pid_path.is_file():
        return False
    pid = int(pid_path.read_text(encoding="utf-8").strip())
    os.kill(pid, signal.SIGTERM)
    return True
