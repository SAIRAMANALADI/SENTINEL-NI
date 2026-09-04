"""Tests for optional authenticated source activity beside remote state telemetry."""

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from src.api.models import RemoteTelemetryBatch
from src.features.network_state import FEATURE_COLUMNS
from src.sensors.runtime import RemoteSensorRuntime, RemoteSensorRuntimeStore


SOURCE = "10.0.0.1"


def _state(timestamp: str = "2018-02-22T01:00:00+00:00") -> dict[str, object]:
    return {
        "timestamp": timestamp,
        "capture_day": "2018-02-22",
        "features": {column: 0.0 for column in FEATURE_COLUMNS},
    }


def _source_row(start: str, *, flow: int, packets: int, bytes_: float, destinations: int, ports: int, source: str = SOURCE) -> dict[str, object]:
    start_time = pd.Timestamp(start)
    return {
        "source_ip": source,
        "capture_day": "2018-02-22",
        "interval_start": start_time.isoformat(),
        "interval_end": (start_time + pd.Timedelta(seconds=10)).isoformat(),
        "flow_count": flow,
        "packet_count": packets,
        "byte_count": bytes_,
        "unique_destinations": destinations,
        "unique_destination_ports": ports,
        "mean_packet_size": bytes_ / max(packets, 1),
        "mean_iat": 1.0,
        "syn_count": 0,
        "ack_count": packets,
        "rst_count": 0,
        "packet_rate": packets / 10.0,
        "byte_rate": bytes_ / 10.0,
    }


def test_remote_source_activity_contract_is_versioned_and_bounded() -> None:
    row = _source_row("2018-02-22T01:00:00+00:00", flow=1, packets=1, bytes_=100, destinations=1, ports=1)
    payload = RemoteTelemetryBatch(
        schema_version="1",
        source_schema_version="1",
        sensor_id="sensor-0123456789abcdef",
        sequence=1,
        sent_at="2026-09-04T01:00:00+00:00",
        states=[_state()],
        source_activity=[row],
    )
    assert str(payload.source_activity[0].source_ip) == SOURCE
    assert payload.model_dump(mode="json")["source_schema_version"] == "1"


def test_remote_state_rejects_wrong_feature_names_even_when_count_is_seventeen() -> None:
    invalid = _state()
    features = dict(invalid["features"])
    features.pop(FEATURE_COLUMNS[0])
    features["unexpected_feature"] = 0.0
    invalid["features"] = features
    with pytest.raises(ValueError, match="frozen 17-feature schema"):
        RemoteTelemetryBatch(
            schema_version="1",
            sensor_id="sensor-0123456789abcdef",
            sequence=1,
            sent_at="2026-09-04T01:00:00+00:00",
            states=[invalid],
        )


def test_remote_source_activity_rejects_duplicates_and_bad_intervals() -> None:
    row = _source_row("2018-02-22T01:00:00+00:00", flow=1, packets=1, bytes_=100, destinations=1, ports=1)
    common = {
        "schema_version": "1",
        "source_schema_version": "1",
        "sensor_id": "sensor-0123456789abcdef",
        "sequence": 1,
        "sent_at": "2026-09-04T01:00:00+00:00",
        "states": [_state()],
    }
    with pytest.raises(ValueError, match="duplicate"):
        RemoteTelemetryBatch(**common, source_activity=[row, row])
    bad = {**row, "interval_end": "2018-02-22T01:00:11+00:00"}
    with pytest.raises(ValueError, match="exactly 10 seconds"):
        RemoteTelemetryBatch(**common, source_activity=[bad])


def test_remote_runtime_ranks_current_sources_with_bounded_sensor_scope() -> None:
    runtime = RemoteSensorRuntime(
        "sensor-0123456789abcdef",
        inference_fn=lambda _frame: {"forecast": [{"score": 0.4, "warning": True}]},
    )
    runtime.ingest(
        [_state()],
        [
            _source_row("2018-02-22T01:00:00+00:00", flow=1, packets=1, bytes_=100, destinations=1, ports=1),
            _source_row("2018-02-22T01:00:10+00:00", flow=2, packets=10, bytes_=10_000, destinations=3, ports=3),
        ],
        received_at=datetime.now(timezone.utc),
    )
    snapshot = runtime.snapshot()
    assert snapshot["source_status"] == "SOURCE_ATTRIBUTION_AVAILABLE"
    assert snapshot["source_attribution"]["sensor_id"] == "sensor-0123456789abcdef"
    assert snapshot["source_priorities"][0]["priority"] == "HIGH PRIORITY SOURCE"
    assert snapshot["source_priorities"][0]["sensor_id"] == "sensor-0123456789abcdef"

    isolated = RemoteSensorRuntimeStore(inference_fn=lambda _frame: {"forecast": []})
    isolated.ingest("sensor-0123456789abcdef", [_state()], [])
    isolated.ingest("sensor-fedcba9876543210", [_state()], [])
    assert isolated.snapshot("sensor-fedcba9876543210")["source_status"] == "NO_SOURCE_ATTRIBUTION"


def test_remote_runtime_marks_source_data_stale_without_erasing_history() -> None:
    now = [datetime(2026, 9, 4, 1, 0, tzinfo=timezone.utc)]
    runtime = RemoteSensorRuntime("sensor-0123456789abcdef", clock=lambda: now[0])
    runtime.ingest(
        [_state()],
        [_source_row("2018-02-22T01:00:00+00:00", flow=1, packets=1, bytes_=100, destinations=1, ports=1)],
    )
    now[0] += timedelta(seconds=31)
    snapshot = runtime.snapshot()
    assert snapshot["source_status"] == "SOURCE_DATA_STALE"
    assert snapshot["source_priorities"]
