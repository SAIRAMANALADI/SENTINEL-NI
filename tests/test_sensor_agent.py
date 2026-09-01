"""Unit tests for the bounded remote-agent primitives."""

from __future__ import annotations

from pathlib import Path

from src.agent.buffer import DiskTelemetryBuffer
from src.agent.collector import AgentCollector
from src.agent.config import AgentConfig


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
