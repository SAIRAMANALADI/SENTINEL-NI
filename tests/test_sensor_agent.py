"""Unit tests for the bounded remote-agent primitives."""

from __future__ import annotations

from pathlib import Path
from datetime import datetime, timezone

from src.agent.buffer import DiskTelemetryBuffer
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
