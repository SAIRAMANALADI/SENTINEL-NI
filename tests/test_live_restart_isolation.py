"""Acceptance tests for clean live-session boundaries."""

from __future__ import annotations

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
        "model_version": "restart-test-model",
        "reference_timestamp": reference,
        "threshold": 0.19,
        "operating_mode": "balanced",
        "forecast": [
            {
                "step": step,
                "horizon_seconds": step * 10,
                "timestamp": (pd.Timestamp(reference) + pd.Timedelta(seconds=step * 10)).isoformat(),
                "score": 0.1,
                "warning": False,
            }
            for step in range(1, 6)
        ],
        "explanation": {},
    }


def test_restart_isolates_history_sources_and_mitigation() -> None:
    store = LiveRuntimeStore(inference_fn=_fake_inference)
    for index in range(11):
        store.ingest_event(_packet(index))

    before = store.snapshot({"status": "LIVE_RUNNING", "available": True, "event_count": 11})
    assert before["forecast"]["status"] == "READY"

    store.start_session()
    after = store.snapshot({"status": "LIVE_RUNNING", "available": True, "event_count": 0})

    assert after["state"]["valid_state_count"] == 0
    assert after["state"]["buffer_size"] == 0
    assert after["forecast"]["status"] == "WAITING_FOR_LIVE_HISTORY"
    assert after["forecast"]["horizons"] == []
    assert after["forecast"]["last_forecast"]["stale"] is True
    assert after["source_priorities"] == []
    assert after["mitigation"]["recommendations"] == []


def test_restart_does_not_mark_old_forecast_as_current() -> None:
    store = LiveRuntimeStore(inference_fn=_fake_inference)
    for index in range(11):
        store.ingest_event(_packet(index))
    store.start_session()

    stopped = store.snapshot({"status": "LIVE_STOPPED", "available": True, "event_count": 0})
    assert stopped["telemetry"]["readiness_state"] == "STALE"
    assert stopped["forecast"]["status"] == "WAITING_FOR_LIVE_HISTORY"
    assert stopped["forecast"]["last_forecast"]["status"] == "STALE_NOT_LIVE"
