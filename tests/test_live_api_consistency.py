"""Consistency checks for the live API response contract."""

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
        "model_version": "consistency-test-model",
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


def test_waiting_response_has_no_current_scores() -> None:
    store = LiveRuntimeStore(inference_fn=_fake_inference)
    snapshot = store.snapshot({"status": "LIVE_RUNNING", "available": True, "event_count": 1})

    assert snapshot["forecast"]["status"] == "WAITING_FOR_LIVE_HISTORY"
    assert snapshot["state"]["buffer_size"] < snapshot["state"]["buffer_required"]
    assert snapshot["forecast"]["forecast_scores"] == []
    assert snapshot["forecast"]["warning_states"] == []


def test_ready_response_has_a_full_buffer_and_scores() -> None:
    store = LiveRuntimeStore(inference_fn=_fake_inference)
    for index in range(11):
        store.ingest_event(_packet(index))
    snapshot = store.snapshot({"status": "LIVE_RUNNING", "available": True, "event_count": 11})

    assert snapshot["forecast"]["status"] == "READY"
    assert snapshot["state"]["buffer_size"] >= snapshot["state"]["buffer_required"]
    assert len(snapshot["forecast"]["forecast_scores"]) == 5
    assert len(snapshot["forecast"]["warning_states"]) == 5


def test_stopped_response_is_not_current_live() -> None:
    store = LiveRuntimeStore(inference_fn=_fake_inference)
    for index in range(11):
        store.ingest_event(_packet(index))
    snapshot = store.snapshot({"status": "LIVE_STOPPED", "available": True, "event_count": 11})

    assert snapshot["forecast"]["status"] == "STALE_NOT_LIVE"
    assert snapshot["forecast"]["stale"] is True
    assert snapshot["telemetry"]["readiness_state"] == "STALE"


def test_packet_quality_fields_are_consistent() -> None:
    store = LiveRuntimeStore(inference_fn=_fake_inference)
    store.ingest_event(_packet(0))
    snapshot = store.snapshot(
        {
            "status": "LIVE_RUNNING",
            "available": True,
            "event_count": 1,
            "parse_error_count": 2,
            "dropped_count": 0,
            "parse_error_categories": {"non_ip": 2},
        }
    )
    quality = snapshot["telemetry"]["packet_quality"]
    assert quality["packets_seen"] == 3
    assert quality["valid_events"] == 1
    assert quality["ignored_events"] == 2
    assert quality["ignored_categories"] == {"non_ip": 2}
