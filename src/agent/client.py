"""Remote sensor client with bounded disk buffering and retry-safe delivery."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
import os
from pathlib import Path
import random
import re
import signal
import time
from typing import Any

from src.agent.buffer import BufferFullError, DiskTelemetryBuffer
from src.agent.collector import AgentCollector
from src.agent.config import AgentConfig
from src.agent.identity import hostname, validate_registration_response
from src.agent.telemetry import TelemetryBatcher
from src.agent.transport import TransportError, request_json
from src.agent.validation import validate_startup
from src.telemetry.live import LiveTelemetryAdapter
from src.streaming.source_activity import SOURCE_ACTIVITY_COLUMNS
from src.platform.logging import configure_logging, get_logger, log_event


LOGGER = get_logger(__name__)
TRANSIENT_HTTP_STATUSES = frozenset({408, 425, 429, 500, 502, 503, 504})
TELEMETRY_ACK_STATUSES = frozenset({"ACCEPTED", "DUPLICATE_ACKNOWLEDGED"})


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _is_transient(error: TransportError) -> bool:
    return error.status_code is None or error.status_code in TRANSIENT_HTTP_STATUSES


class SensorClient:
    def __init__(self, config: AgentConfig) -> None:
        self.config = config

    def _transport_options(self) -> dict[str, Any]:
        return {
            "timeout": self.config.connection_timeout_seconds,
            "ca_path": str(self.config.tls_ca_path) if self.config.tls_ca_path else None,
            "client_cert_path": str(self.config.tls_client_cert_path) if self.config.tls_client_cert_path else None,
            "client_key_path": str(self.config.tls_client_key_path) if self.config.tls_client_key_path else None,
            "verify_tls": self.config.tls_verify,
        }

    def _url(self, path: str) -> str:
        return f"{self.config.server_url.rstrip('/')}{path}"

    def register(self, enrollment_token: str) -> dict[str, Any]:
        if not isinstance(enrollment_token, str) or not enrollment_token.strip():
            raise ValueError("enrollment_token must be a non-empty string")
        result = request_json(
            self.config.server_url,
            "/api/v1/sensors/register",
            method="POST",
            payload={"enrollment_token": enrollment_token, "hostname": hostname(), "agent_version": self.config.agent_version},
            **self._transport_options(),
        )
        validate_registration_response(result)
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
            **self._transport_options(),
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
            source_activity_count=len(payload.get("source_activity", [])),
        )
        result = request_json(
            self.config.server_url,
            "/api/v1/telemetry",
            method="POST",
            headers={"X-Sentinel-Sensor-Token": self.config.runtime_token or ""},
            payload=payload,
            **self._transport_options(),
        )
        if str(result.get("status", "")).upper() not in TELEMETRY_ACK_STATUSES:
            raise TransportError("central service returned an invalid telemetry acknowledgment")
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
            **self._transport_options(),
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
        self._pending_source_activity: deque[dict[str, Any]] = deque(
            maxlen=max(240, config.batch_size * 20)
        )
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
        self._connection_status = "DISCONNECTED"
        self._counters = {
            "states_collected": 0,
            "source_activity_rows_collected": 0,
            "batches_sent": 0,
            "batches_buffered": 0,
            "retries": 0,
            "permanent_rejections": 0,
        }
        self._batcher = TelemetryBatcher(
            config.sensor_id or "",
            sequence_start=config.next_sequence,
            batch_size=config.batch_size,
            on_sequence_advanced=self._persist_next_sequence,
        )

    def _persist_next_sequence(self, next_sequence: int) -> None:
        self.config.next_sequence = next_sequence
        self.config.save()

    def _payload(
        self,
        states: list[dict[str, Any]],
        source_activity: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        payload = self._batcher.build(states, source_activity=source_activity)
        log_event(
            LOGGER,
            "telemetry batch created",
            event_type="telemetry_batch_created",
            sensor_id=self.config.sensor_id,
            sequence=payload["sequence"],
            state_count=len(states),
            source_activity_count=len(source_activity or []),
        )
        return payload

    def submit_states(
        self,
        states: list[dict[str, Any]],
        source_activity: list[dict[str, Any]] | None = None,
    ) -> str:
        if not states:
            return "empty"
        payload = self._payload(states, source_activity)
        # Never send a newer sequence ahead of an older batch already queued
        # on disk. The central registry accepts monotonic sequences and will
        # reject that otherwise-valid newer batch as a later replay conflict.
        if self.buffer.count:
            self._enqueue_payload(payload)
            return "buffered"
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
            self._enqueue_payload(payload, status_code=exc.status_code)
            return "buffered"

    def _enqueue_payload(self, payload: dict[str, Any], *, status_code: int | None = None) -> None:
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
            "telemetry buffered",
            event_type="telemetry_buffered",
            sensor_id=self.config.sensor_id,
            sequence=payload["sequence"],
            status_code=status_code,
        )
        self._counters["batches_buffered"] += 1

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
        self._connection_status = "CONNECTED"

    def _remember_error(self, error: Exception, category: str) -> None:
        message = str(error)
        if self.config.runtime_token:
            message = message.replace(self.config.runtime_token, "<redacted>")
        message = re.sub(r"(?i)(bearer\s+)[^\s,;]+", r"\1<redacted>", message)
        self._last_error = message[:240]
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
            self._connection_status = "DISCONNECTED"
            return False
        except Exception as exc:
            self._remember_error(exc, "heartbeat_error")
            self._connection_status = "DISCONNECTED"
            return False
        self._last_heartbeat_at = _utc_now()
        self._connection_status = "CONNECTED"
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

    def _on_source_activity(self, activity: Any) -> bool:
        """Queue bounded JSON-safe source rows beside the next state batch."""

        rows = activity.to_dict(orient="records")
        if len(self._pending_source_activity) + len(rows) > self._pending_source_activity.maxlen:
            return False
        for row in rows:
            copied = {column: row[column] for column in SOURCE_ACTIVITY_COLUMNS}
            copied["interval_start"] = copied["interval_start"].isoformat()
            copied["interval_end"] = copied["interval_end"].isoformat()
            copied["capture_day"] = str(copied["capture_day"])
            copied["flow_count"] = int(copied["flow_count"])
            copied["packet_count"] = int(copied["packet_count"])
            copied["unique_destinations"] = int(copied["unique_destinations"])
            copied["unique_destination_ports"] = int(copied["unique_destination_ports"])
            copied["syn_count"] = int(copied["syn_count"])
            copied["ack_count"] = int(copied["ack_count"])
            copied["rst_count"] = int(copied["rst_count"])
            for field in ("byte_count", "mean_packet_size", "mean_iat", "packet_rate", "byte_rate"):
                copied[field] = float(copied[field])
            self._pending_source_activity.append(copied)
        self._counters["source_activity_rows_collected"] += len(rows)
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
            source_count = min(120, len(self._pending_source_activity))
            source_activity = [self._pending_source_activity.popleft() for _ in range(source_count)]
            try:
                self.submit_states(states, source_activity)
            except BufferFullError as exc:
                # The state has not been durably queued. Put both queues back
                # in their original order so capture never silently loses a
                # batch under REJECT_NEW or a byte limit.
                for state in reversed(states):
                    self._pending.appendleft(state)
                for row in reversed(source_activity):
                    self._pending_source_activity.appendleft(row)
                self._remember_error(exc, "telemetry_buffer_full")
                return
            except Exception as exc:
                # A permanent rejection is quarantined by submit_states. Keep
                # the capture loop alive and expose the failure in status.
                self._remember_error(exc, "telemetry_delivery_error")
            self._pending_since = time.monotonic() if self._pending else None

    def run(self) -> None:
        startup = validate_startup(self.config)
        configure_logging(
            self.config.log_level,
            log_path=self.config.log_path,
            max_bytes=self.config.log_max_bytes,
            backup_count=self.config.log_backup_count,
        )
        log_event(LOGGER, "agent startup validated", event_type="agent_startup_validated", sensor_id=self.config.sensor_id)
        self.config.pid_path.parent.mkdir(parents=True, exist_ok=True)
        _stop_request_path(self.config.pid_path).unlink(missing_ok=True)
        self.config.pid_path.write_text(str(os.getpid()), encoding="utf-8")
        self._collector = AgentCollector(
            interface=self.config.interface or "",
            on_state=self._on_state,
            on_source_activity=self._on_source_activity,
        )
        self._adapter = LiveTelemetryAdapter(
            self.config.interface,
            capture_filter=self.config.capture_filter,
            event_callback=self._collector.ingest_event,
            queue_size=max(1000, self.config.batch_size * 8),
        )
        self._running = True
        previous_handlers: dict[int, Any] = {}

        def request_shutdown(signum: int, _frame: Any) -> None:
            log_event(LOGGER, "agent shutdown requested", event_type="shutdown_requested", sensor_id=self.config.sensor_id, status_code=signum)
            self.stop()

        try:
            for signal_number in (signal.SIGTERM, signal.SIGINT):
                previous_handlers[signal_number] = signal.getsignal(signal_number)
                signal.signal(signal_number, request_shutdown)
            self._capture_status = "STARTING"
            self._adapter.start()
            self._capture_status = "RUNNING"
            self._heartbeat()
            self._last_heartbeat = time.monotonic()
            while self._running:
                if _stop_requested(self.config.pid_path, os.getpid()):
                    log_event(
                        LOGGER,
                        "agent shutdown requested",
                        event_type="shutdown_requested",
                        sensor_id=self.config.sensor_id,
                        status_code=0,
                    )
                    self.stop()
                    continue
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
            try:
                if self._adapter is not None:
                    self._adapter.stop()
            except Exception as exc:
                self._remember_error(exc, "capture_shutdown_error")
            try:
                if self._collector is not None:
                    self._collector.flush()
            except Exception as exc:
                self._remember_error(exc, "collector_shutdown_error")
            try:
                self._drain_pending(force=True)
            except Exception as exc:
                self._remember_error(exc, "pending_shutdown_error")
            try:
                self.flush_buffer()
            except Exception as exc:
                self._remember_error(exc, "shutdown_flush_error")
            try:
                self.config.pid_path.unlink()
            except FileNotFoundError:
                pass
            _stop_request_path(self.config.pid_path).unlink(missing_ok=True)
            for signal_number, previous in previous_handlers.items():
                signal.signal(signal_number, previous)
            self._running = False
            self._capture_status = "STOPPED"
            log_event(LOGGER, "agent stopped", event_type="agent_stopped", sensor_id=self.config.sensor_id)

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
            "process_status": "RUNNING" if self._running else "STOPPED",
            "capture_status": self._capture_status,
            "connection_status": self._connection_status,
            "telemetry_status": "FRESH" if telemetry_age is not None and telemetry_age <= self.config.heartbeat_interval_seconds * 2 else ("STALE" if telemetry_age is not None else "UNKNOWN"),
            "last_heartbeat": self._last_heartbeat_at.isoformat() if self._last_heartbeat_at else None,
            "last_telemetry": self._last_telemetry_at.isoformat() if self._last_telemetry_at else None,
            "last_state_timestamp": self._last_state_timestamp,
            "last_sent_sequence": self._last_sent_sequence,
            "last_acknowledged_sequence": self._last_acknowledged_sequence,
            "last_error": self._last_error,
            "pending_source_activity_rows": len(self._pending_source_activity),
            "buffer": self.buffer.status,
            "counters": dict(self._counters),
            "config": self.config.redacted(),
        }


STOP_TIMEOUT_SECONDS = 10.0
_WINDOWS_STILL_ACTIVE = 259
_WINDOWS_ERROR_ACCESS_DENIED = 5
_WINDOWS_ERROR_INVALID_PARAMETER = 87
_WINDOWS_ERROR_NOT_FOUND = 1168


def _stop_request_path(pid_path: Path) -> Path:
    return pid_path.with_name(f"{pid_path.name}.stop")


def _process_exists(pid: int) -> bool:
    """Check liveness without sending a signal to an arbitrary process."""

    if os.name != "nt":
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError as exc:
            raise RuntimeError(f"permission denied inspecting agent process {pid}") from exc
        return True

    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        error = ctypes.get_last_error()
        if error in {_WINDOWS_ERROR_INVALID_PARAMETER, _WINDOWS_ERROR_NOT_FOUND}:
            return False
        if error == _WINDOWS_ERROR_ACCESS_DENIED:
            raise RuntimeError(f"permission denied inspecting agent process {pid}")
        raise OSError(error, f"unable to inspect agent process {pid}")
    try:
        exit_code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            error = ctypes.get_last_error()
            raise OSError(error, f"unable to inspect agent process {pid}")
        return exit_code.value == _WINDOWS_STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)


def _stop_requested(path: str | Path, pid: int) -> bool:
    request_path = _stop_request_path(Path(path))
    try:
        return request_path.read_text(encoding="utf-8").strip() == str(pid)
    except (FileNotFoundError, OSError):
        return False


def _write_stop_request(pid_path: Path, pid: int) -> Path:
    request_path = _stop_request_path(pid_path)
    temporary = request_path.with_name(f".{request_path.name}-{os.getpid()}")
    temporary.write_text(str(pid), encoding="utf-8")
    temporary.replace(request_path)
    return request_path


def stop_pid(path: str | Path, *, timeout_seconds: float = STOP_TIMEOUT_SECONDS) -> bool:
    """Request an agent-specific graceful stop and verify process exit.

    A PID file is only a rendezvous point. The stop command never terminates
    the PID directly, so a stale or incorrect PID cannot kill an unrelated
    process. The foreground agent consumes a request containing its own PID
    and performs the normal capture/buffer/transport cleanup in ``finally``.
    """

    pid_path = Path(path)
    if not pid_path.is_file():
        return False
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be a positive number")
    try:
        pid = int(pid_path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError) as exc:
        raise RuntimeError(f"agent PID file is malformed: {pid_path}") from exc
    if pid <= 0:
        raise RuntimeError(f"agent PID file contains an invalid process id: {pid_path}")

    if not _process_exists(pid):
        pid_path.unlink(missing_ok=True)
        return False

    request_path = _write_stop_request(pid_path, pid)
    deadline = time.monotonic() + float(timeout_seconds)
    try:
        while _process_exists(pid):
            if time.monotonic() >= deadline:
                raise RuntimeError(
                    f"agent process {pid} did not stop within {timeout_seconds:g}s; no process was terminated"
                )
            time.sleep(0.05)
    finally:
        request_path.unlink(missing_ok=True)
    pid_path.unlink(missing_ok=True)
    return True
