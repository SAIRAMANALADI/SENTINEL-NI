"""Focused runtime truthfulness tests for strict remote history resets."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.features.network_state import FEATURE_COLUMNS
from src.sensors.runtime import RemoteSensorRuntime


def _state(timestamp: datetime) -> dict[str, object]:
    return {
        "timestamp": timestamp.isoformat(),
        "capture_day": timestamp.date().isoformat(),
        "features": {column: 0.0 for column in FEATURE_COLUMNS},
    }


def test_history_reset_clears_forecast_until_new_l10_sequence() -> None:
    runtime = RemoteSensorRuntime(
        "sensor-test",
        inference_fn=lambda sequence: {"forecast": [{"score": 0.1}], "threshold": 0.19},
    )
    start = datetime(2026, 9, 4, 10, 0, tzinfo=timezone.utc)
    runtime.ingest([_state(start + timedelta(seconds=10 * index)) for index in range(10)])
    assert runtime.snapshot()["forecast_status"] == "FORECAST_READY"

    runtime.ingest([_state(start + timedelta(seconds=110))])
    snapshot = runtime.snapshot()
    assert snapshot["history_length"] == 1
    assert snapshot["forecast_status"] == "BUILDING_HISTORY"
    assert snapshot["forecast"] is None
