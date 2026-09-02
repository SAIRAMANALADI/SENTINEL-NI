"""Unit tests for the bounded remote-agent primitives."""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone
import json

import pytest

from src.agent.buffer import BufferFullError, DiskTelemetryBuffer
from src.agent.collector import AgentCollector
from src.agent.config import AgentConfig
from src.agent.client import SensorAgent
from src.agent.telemetry import TelemetryBatcher
from src.agent.transport import TransportError
from src.features.network_state import FEATURE_COLUMNS


def test_disk_buffer_is_ordered_and_recoverable(tmp_path: Path) -> None:
    buffer = DiskTelemetryBuffer(tmp_path / "buffer", max_batches=2, max_bytes=10_000)
    buffer.enqueue({"sequence": 2, "states": []})
    buffer.enqueue({"sequence": 1, "states": []})
    assert buffer.count == 2
    assert buffer.peek()["sequence"] == 1  # type: ignore[index]
    buffer.pop(1)
    assert buffer.peek()["sequence"] == 2  # type: ignore[index]


def test_disk_buffer_overflow_is_explicit_and_corruption_is_quarantined(tmp_path: Path) -> None:
    path = tmp_path / "buffer"
    buffer = DiskTelemetryBuffer(path, max_batches=1, max_bytes=10_000, overflow_policy="DROP_OLDEST")
    buffer.enqueue({"sequence": 1, "states": []})
    buffer.enqueue({"sequence": 2, "states": []})
    assert buffer.peek()["sequence"] == 2  # type: ignore[index]
    assert buffer.status["dropped_batches"] == 1
    buffer.pop(2)

    (path / "batch-00000000000000000003.json").write_text("{not json", encoding="utf-8")
    (path / ".batch-crash-left").write_text("partial", encoding="utf-8")
    recovered = DiskTelemetryBuffer(path, max_batches=2, max_bytes=10_000)
    assert recovered.peek() is None
    assert recovered.status["corrupt_batches"] == 1
    assert recovered.status["partial_batches"] == 1
    assert list((path / "quarantine").iterdir())


def test_disk_buffer_can_reject_new_items_without_silent_eviction(tmp_path: Path) -> None:
    buffer = DiskTelemetryBuffer(tmp_path / "buffer", max_batches=1, max_bytes=10_000, overflow_policy="REJECT_NEW")
    buffer.enqueue({"sequence": 1, "states": []})
    with pytest.raises(BufferFullError):
        buffer.enqueue({"sequence": 2, "states": []})
    assert buffer.peek()["sequence"] == 1  # type: ignore[index]


def test_agent_config_redacts_runtime_secret(tmp_path: Path) -> None:
    config = AgentConfig(runtime_token="secret", buffer_dir=tmp_path / "buffer", pid_path=tmp_path / "agent.pid")
    path = config.save(tmp_path / "config.json")
    loaded = AgentConfig.load(path)
    assert loaded.redacted()["runtime_token"] == "<configured>"
    assert "secret" not in str(loaded.redacted())


def test_collector_does_not_claim_raw_packet_retention() -> None:
    collector = AgentCollector(interface="test", on_state=lambda _: True)
    assert collector.status()["raw_packets_retained"] is False


def _state(index: int = 0) -> dict[str, object]:
    return {
        "timestamp": f"2018-02-22T01:00:{index * 10:02d}+00:00",
        "capture_day": "2018-02-22",
        "features": {column: float(index) for column in FEATURE_COLUMNS},
    }


def test_telemetry_batcher_assigns_bounded_monotonic_envelopes() -> None:
    sent_at = datetime(2026, 9, 2, 12, 0, tzinfo=timezone.utc)
    batcher = TelemetryBatcher(
        "sensor-0123456789abcdef",
        sequence_start=7,
        batch_size=2,
        clock=lambda: sent_at,
    )
    first = batcher.build([_state(0), _state(1)])
    second = batcher.build([_state(2)])
    assert first["sequence"] == 7
    assert second["sequence"] == 8
    assert first["sensor_id"] == second["sensor_id"] == "sensor-0123456789abcdef"
    assert first["sent_at"] == "2026-09-02T12:00:00+00:00"
    assert len(first["states"]) == 2
    assert batcher.next_sequence == 9


def test_telemetry_batcher_collects_and_flushes_without_unbounded_memory() -> None:
    batcher = TelemetryBatcher("sensor-0123456789abcdef", batch_size=2)
    assert batcher.add(_state(0)) is None
    assert batcher.pending_count == 1
    full = batcher.add(_state(1))
    assert full is not None
    assert len(full["states"]) == 2
    assert batcher.pending_count == 0
    assert batcher.add(_state(2)) is None
    partial = batcher.flush()
    assert partial is not None
    assert len(partial["states"]) == 1
    assert batcher.flush() is None


def test_telemetry_batcher_rejects_invalid_identity_and_size() -> None:
    try:
        TelemetryBatcher("sensor-not-registered")
    except ValueError as exc:
        assert "sensor_id" in str(exc)
    else:
        raise AssertionError("invalid sensor identity should be rejected")
    batcher = TelemetryBatcher("sensor-0123456789abcdef", batch_size=1)
    try:
        batcher.build([_state(0), _state(1)])
    except ValueError as exc:
        assert "batch size" in str(exc)
    else:
        raise AssertionError("oversized batch should be rejected")


def test_agent_buffers_transient_failures_and_retries_in_sequence_order(tmp_path: Path) -> None:
    config = AgentConfig(
        server_url="http://127.0.0.1:8000",
        sensor_id="sensor-0123456789abcdef",
        runtime_token="snr_test",
        interface="test",
        buffer_dir=tmp_path / "buffer",
        pid_path=tmp_path / "agent.pid",
    )
    config_path = tmp_path / "config.json"
    config.save(config_path)
    agent = SensorAgent(AgentConfig.load(config_path))
    calls: list[int] = []

    def fail_once(payload: dict[str, object]) -> dict[str, object]:
        calls.append(int(payload["sequence"]))
        if len(calls) == 1:
            raise TransportError("temporarily unavailable")
        return {"status": "ACCEPTED"}

    agent.client.telemetry = fail_once  # type: ignore[method-assign]
    assert agent.submit_states([_state(0)]) == "buffered"
    assert agent.buffer.count == 1
    assert agent.flush_buffer() == 1
    assert calls == [1, 1]
    assert agent.buffer.count == 0


def test_agent_records_permanent_rejection_and_does_not_queue_it(tmp_path: Path) -> None:
    config = AgentConfig(
        server_url="http://127.0.0.1:8000", sensor_id="sensor-0123456789abcdef", runtime_token="snr_test",
        interface="test", buffer_dir=tmp_path / "buffer", pid_path=tmp_path / "agent.pid",
    )
    agent = SensorAgent(config)
    agent.client.telemetry = lambda payload: (_ for _ in ()).throw(TransportError("unauthorized", status_code=401))  # type: ignore[method-assign]
    with pytest.raises(RuntimeError):
        agent.submit_states([_state(0)])
    assert agent.buffer.count == 0
    rejected = list((tmp_path / "buffer" / "rejected").glob("*.json"))
    assert len(rejected) == 1
    assert json.loads(rejected[0].read_text(encoding="utf-8"))["status_code"] == 401


def test_agent_local_status_is_truthful_and_redacted(tmp_path: Path) -> None:
    config = AgentConfig(
        server_url="http://central.example:8000", sensor_id="sensor-0123456789abcdef", runtime_token="snr_secret",
        interface="test", buffer_dir=tmp_path / "buffer", pid_path=tmp_path / "agent.pid",
    )
    status = SensorAgent(config).local_status()
    assert status["sensor_id"] == "sensor-0123456789abcdef"
    assert status["agent_status"] == "STOPPED"
    assert status["telemetry_status"] == "UNKNOWN"
    assert status["buffer"]["overflow_policy"] == "DROP_OLDEST"
    assert "snr_secret" not in json.dumps(status)


def test_agent_sequence_continues_after_restart(tmp_path: Path) -> None:
    config = AgentConfig(
        server_url="http://127.0.0.1:8000", sensor_id="sensor-0123456789abcdef", runtime_token="snr_test",
        interface="test", buffer_dir=tmp_path / "buffer", pid_path=tmp_path / "agent.pid",
    )
    path = config.save(tmp_path / "agent.json")
    first = SensorAgent(AgentConfig.load(path))
    sent: list[int] = []
    first.client.telemetry = lambda payload: sent.append(int(payload["sequence"])) or {"status": "ACCEPTED"}  # type: ignore[method-assign]
    assert first.submit_states([_state(0)]) == "sent"

    second = SensorAgent(AgentConfig.load(path))
    second.client.telemetry = lambda payload: sent.append(int(payload["sequence"])) or {"status": "ACCEPTED"}  # type: ignore[method-assign]
    assert second.submit_states([_state(1)]) == "sent"
    assert sent == [1, 2]


def test_agent_retry_backoff_is_bounded(tmp_path: Path) -> None:
    config = AgentConfig(
        server_url="http://127.0.0.1:8000", sensor_id="sensor-0123456789abcdef", runtime_token="snr_test",
        interface="test", buffer_dir=tmp_path / "buffer", pid_path=tmp_path / "agent.pid",
        retry_base_seconds=0.01, retry_max_seconds=0.02,
    )
    agent = SensorAgent(config)
    agent.client.telemetry = lambda payload: (_ for _ in ()).throw(TransportError("timeout"))  # type: ignore[method-assign]
    assert agent.submit_states([_state(0)]) == "buffered"
    assert agent.flush_buffer() == 0
    assert agent._retry_delay == 0.02
    assert agent._next_retry_at > 0


def test_heartbeat_failure_is_visible_without_stopping_collection(tmp_path: Path) -> None:
    config = AgentConfig(
        server_url="http://127.0.0.1:8000", sensor_id="sensor-0123456789abcdef", runtime_token="snr_test",
        interface="test", buffer_dir=tmp_path / "buffer", pid_path=tmp_path / "agent.pid",
    )
    agent = SensorAgent(config)
    agent.client.heartbeat = lambda count, **metadata: (_ for _ in ()).throw(TransportError("central unavailable"))  # type: ignore[method-assign]
    assert agent._heartbeat() is False
    assert agent.local_status()["last_error"] == "central unavailable"
    assert agent.local_status()["agent_status"] == "STOPPED"
