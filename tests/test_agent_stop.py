"""Focused Windows-safe foreground-agent stop and cadence tests."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import time

import pandas as pd
import pytest

from src.agent.client import _process_exists, _stop_request_path, stop_pid
from src.agent.collector import AgentCollector
from src.features.network_state import FEATURE_COLUMNS


def _wait_for_file(path: Path, timeout: float = 3.0) -> None:
    deadline = time.monotonic() + timeout
    while not path.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert path.exists()


def test_stop_running_foreground_process_requests_graceful_exit(tmp_path: Path) -> None:
    pid_path = tmp_path / "agent.pid"
    script = """
import os
from pathlib import Path
import sys
import time
from src.agent.client import _stop_requested

pid_path = Path(sys.argv[1])
pid_path.write_text(str(os.getpid()), encoding="utf-8")
while not _stop_requested(pid_path, os.getpid()):
    time.sleep(0.01)
pid_path.unlink(missing_ok=True)
"""
    process = subprocess.Popen([sys.executable, "-c", script, str(pid_path)])
    try:
        _wait_for_file(pid_path)
        assert stop_pid(pid_path, timeout_seconds=3.0) is True
        assert process.wait(timeout=3.0) == 0
        assert not pid_path.exists()
        assert not _stop_request_path(pid_path).exists()
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=3.0)


def test_stop_nonexistent_or_stale_agent_is_idempotent(tmp_path: Path) -> None:
    missing = tmp_path / "missing.pid"
    assert stop_pid(missing) is False

    stale = tmp_path / "stale.pid"
    stale.write_text("2147483647", encoding="utf-8")
    assert stop_pid(stale, timeout_seconds=0.2) is False
    assert not stale.exists()


def test_wrong_pid_never_terminates_unrelated_process(tmp_path: Path) -> None:
    pid_path = tmp_path / "wrong.pid"
    pid_path.write_text(str(os.getpid()), encoding="utf-8")
    with pytest.raises(RuntimeError, match="no process was terminated"):
        stop_pid(pid_path, timeout_seconds=0.1)
    assert _process_exists(os.getpid())
    assert not _stop_request_path(pid_path).exists()


def _packet(timestamp: str, source_port: int) -> dict[str, object]:
    return {
        "timestamp": timestamp,
        "source_ip": "10.0.0.2",
        "destination_ip": "10.0.0.20",
        "source_port": source_port,
        "destination_port": 443,
        "protocol": "TCP",
        "packet_length": 100,
        "tcp_flags": "FIN",
    }


def test_remote_collector_emits_canonical_empty_intervals_for_real_gaps() -> None:
    states: list[dict[str, object]] = []
    collector = AgentCollector(interface="test", on_state=states.append)
    collector.ingest_event(_packet("2026-09-04T10:00:00+00:00", 1000))
    collector.ingest_event(_packet("2026-09-04T10:00:20+00:00", 1001))

    assert [row["timestamp"] for row in states] == [
        "2026-09-04T10:00:00+00:00",
        "2026-09-04T10:00:10+00:00",
    ]
    assert all(list(row) == FEATURE_COLUMNS + ["timestamp", "capture_day"] for row in states)
    empty = pd.DataFrame([states[1]])
    assert empty[FEATURE_COLUMNS].to_numpy(dtype="float64").tolist() == [[0.0] * 17]


def test_remote_collector_uses_last_capture_time_for_late_flow_completion() -> None:
    states: list[dict[str, object]] = []
    collector = AgentCollector(interface="test", on_state=states.append)

    # Keep the first flow open across several 10-second windows.  A separate
    # flow closes at t=20, then the long-lived flow closes at t=40.
    collector.ingest_event({
        **_packet("2026-09-04T10:00:00+00:00", 1000),
        "tcp_flags": "SYN",
    })
    collector.ingest_event(_packet("2026-09-04T10:00:20+00:00", 1001))
    collector.ingest_event({
        **_packet("2026-09-04T10:00:25+00:00", 1000),
        "tcp_flags": "ACK",
    })
    collector.ingest_event(_packet("2026-09-04T10:00:30+00:00", 1002))
    collector.ingest_event(_packet("2026-09-04T10:00:40+00:00", 1000))
    collector.ingest_event(_packet("2026-09-04T10:00:50+00:00", 1003))

    timestamps = [pd.Timestamp(row["timestamp"]) for row in states]
    assert timestamps == sorted(timestamps)
    assert timestamps == [
        pd.Timestamp("2026-09-04T10:00:20+00:00"),
        pd.Timestamp("2026-09-04T10:00:30+00:00"),
        pd.Timestamp("2026-09-04T10:00:40+00:00"),
    ]


def test_remote_collector_uses_closing_packet_time_for_idle_completion() -> None:
    states: list[dict[str, object]] = []
    collector = AgentCollector(interface="test", on_state=states.append)

    collector.ingest_event({
        **_packet("2026-09-04T10:00:00+00:00", 1000),
        "tcp_flags": "SYN",
    })
    collector.ingest_event(_packet("2026-09-04T10:00:20+00:00", 1001))
    # At t=30 the builder closes the t=00 flow by idle timeout.  It must be
    # scheduled at the closing packet's capture time, not back at t=00.
    collector.ingest_event(_packet("2026-09-04T10:00:30+00:00", 1002))
    collector.ingest_event(_packet("2026-09-04T10:00:40+00:00", 1003))

    assert [row["timestamp"] for row in states] == [
        "2026-09-04T10:00:20+00:00",
        "2026-09-04T10:00:30+00:00",
    ]


def test_remote_collector_flush_does_not_reemit_an_already_emitted_state() -> None:
    states: list[dict[str, object]] = []
    collector = AgentCollector(interface="test", on_state=states.append)

    # The first flow creates the t=00 state.  The second flow remains active
    # until shutdown with the same last capture time; flush must not replay it.
    collector.ingest_event(_packet("2026-09-04T10:00:00+00:00", 1001))
    collector.ingest_event({
        **_packet("2026-09-04T10:00:00+00:00", 1000),
        "tcp_flags": "SYN",
    })
    collector.ingest_event(_packet("2026-09-04T10:00:10+00:00", 1002))
    assert [row["timestamp"] for row in states] == ["2026-09-04T10:00:00+00:00"]

    collector.flush()
    assert [row["timestamp"] for row in states] == [
        "2026-09-04T10:00:00+00:00",
        "2026-09-04T10:00:10+00:00",
    ]
