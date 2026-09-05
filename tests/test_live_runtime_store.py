"""Tests for the bounded live runtime state and forecast contract."""

from __future__ import annotations

import threading
import time

import pandas as pd

from src.api.live_runtime import LiveRuntimeStore


def _packet(index: int) -> dict[str, object]:
    return {
        "timestamp": (pd.Timestamp("2026-08-25T12:00:00+00:00") + pd.Timedelta(seconds=index * 10)).isoformat(),
        "source_ip": "10.0.0.2",
        "destination_ip": "10.0.0.20",
        "source_port": 1000 + index,
        "destination_port": 443,
        "protocol": "TCP",
        "packet_length": 100 + index,
        "tcp_flags": "FIN",
    }


def _fake_inference(sequence: pd.DataFrame) -> dict[str, object]:
    reference = pd.Timestamp(sequence["timestamp"].iloc[-1]).isoformat()
    return {
        "model_version": "test-model",
        "reference_timestamp": reference,
        "threshold": 0.19,
        "operating_mode": "balanced",
        "forecast": [
            {
                "step": step,
                "horizon_seconds": step * 10,
                "timestamp": (pd.Timestamp(sequence["timestamp"].iloc[-1]) + pd.Timedelta(seconds=step * 10)).isoformat(),
                "score": 0.1 + step / 100.0,
                "warning": False,
            }
            for step in range(1, 6)
        ],
        "explanation": {"causal_claim": False},
    }


def _running_status() -> dict[str, object]:
    return {
        "mode": "live",
        "interface": "Wi-Fi",
        "status": "LIVE_RUNNING",
        "available": True,
        "event_count": 0,
        "last_event_at": None,
        "stale": False,
    }


def test_waiting_state_has_no_fake_forecast() -> None:
    store = LiveRuntimeStore(inference_fn=_fake_inference)
    store.ingest_event(_packet(0))
    snapshot = store.snapshot(_running_status())

    assert snapshot["state"]["valid_state_count"] == 1
    assert snapshot["state"]["buffer_size"] == 1
    assert snapshot["state"]["buffer_required"] == 10
    assert snapshot["forecast"]["status"] == "WAITING_FOR_LIVE_HISTORY"
    assert snapshot["forecast"]["horizons"] == []
    assert snapshot["forecast"]["forecast_scores"] == []


def test_tenth_and_eleventh_states_produce_rolling_forecasts() -> None:
    store = LiveRuntimeStore(inference_fn=_fake_inference)
    for index in range(11):
        store.ingest_event(_packet(index))

    snapshot = store.snapshot(_running_status())
    assert snapshot["state"]["valid_state_count"] == 11
    assert snapshot["state"]["buffer_size"] == 10
    assert snapshot["forecast"]["status"] == "READY"
    assert len(snapshot["forecast"]["horizons"]) == 5
    assert snapshot["forecast_update_count"] == 2
    assert snapshot["forecast"]["reference_timestamp"] == "2026-08-25T12:01:40+00:00"
    assert snapshot["source_priorities"]
    assert all(row["simulation_only"] is True for row in snapshot["mitigation"]["recommendations"])


def test_older_inference_cannot_overwrite_newer_forecast() -> None:
    old_inference_started = threading.Event()
    release_old_inference = threading.Event()

    def out_of_order_inference(sequence: pd.DataFrame) -> dict[str, object]:
        reference = pd.Timestamp(sequence["timestamp"].iloc[-1]).isoformat()
        if reference == "2026-08-25T12:01:30+00:00":
            old_inference_started.set()
            assert release_old_inference.wait(timeout=5)
        return _fake_inference(sequence)

    store = LiveRuntimeStore(inference_fn=out_of_order_inference)

    def feed_first_window() -> None:
        for index in range(10):
            store.ingest_event(_packet(index))

    worker = threading.Thread(target=feed_first_window)
    worker.start()
    assert old_inference_started.wait(timeout=5)
    store.ingest_event(_packet(10))
    release_old_inference.set()
    worker.join(timeout=5)

    snapshot = store.snapshot(_running_status())
    assert not worker.is_alive()
    assert snapshot["forecast"]["reference_timestamp"] == "2026-08-25T12:01:40+00:00"
    assert snapshot["forecast_update_count"] == 1


def test_stop_marks_last_forecast_stale_without_deleting_it() -> None:
    store = LiveRuntimeStore(inference_fn=_fake_inference)
    for index in range(10):
        store.ingest_event(_packet(index))

    stopped = store.snapshot({**_running_status(), "status": "LIVE_STOPPED"})
    assert stopped["forecast"]["status"] == "STALE_NOT_LIVE"
    assert stopped["forecast"]["stale"] is True
    assert len(stopped["forecast"]["horizons"]) == 5


def test_restart_resets_active_history_and_exposes_previous_result_as_stale() -> None:
    store = LiveRuntimeStore(inference_fn=_fake_inference)
    first_session = store.session_id
    for index in range(10):
        store.ingest_event(_packet(index))
    store.start_session()

    restarted = store.snapshot(_running_status())
    assert restarted["session_id"] != first_session
    assert restarted["forecast"]["session_id"] == restarted["session_id"]
    assert restarted["state"]["valid_state_count"] == 0
    assert restarted["state"]["buffer_size"] == 0
    assert restarted["forecast"]["status"] == "WAITING_FOR_LIVE_HISTORY"
    assert restarted["forecast"]["horizons"] == []
    assert restarted["forecast"]["last_forecast"]["stale"] is True
    assert restarted["forecast"]["last_forecast"]["session_id"] == first_session


def test_out_of_order_event_is_rejected_without_latching_global_error() -> None:
    store = LiveRuntimeStore(inference_fn=_fake_inference)
    assert store.ingest_event(_packet(1)) is True
    assert store.ingest_event(_packet(0)) is False

    snapshot = store.snapshot(_running_status())
    assert snapshot["state"]["accepted_event_count"] == 1
    assert snapshot["state"]["rejected_event_count"] == 1
    assert snapshot["state"]["rejected_event_categories"] == {"out_of_order": 1}
    assert snapshot["last_error"] is None
    assert snapshot["telemetry"]["readiness_state"] != "ERROR"


def test_snapshot_is_not_blocked_while_model_inference_runs() -> None:
    inference_started = threading.Event()
    release_inference = threading.Event()

    def blocking_inference(sequence: pd.DataFrame) -> dict[str, object]:
        inference_started.set()
        assert release_inference.wait(timeout=5)
        return _fake_inference(sequence)

    store = LiveRuntimeStore(inference_fn=blocking_inference)

    def feed_history() -> None:
        for index in range(10):
            store.ingest_event(_packet(index))

    worker = threading.Thread(target=feed_history)
    worker.start()
    assert inference_started.wait(timeout=5)

    started = time.perf_counter()
    snapshot = store.snapshot(_running_status())
    elapsed = time.perf_counter() - started
    release_inference.set()
    worker.join(timeout=5)

    assert elapsed < 0.5
    assert snapshot["state"]["buffer_size"] == 10
    assert not worker.is_alive()
