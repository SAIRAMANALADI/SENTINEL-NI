"""Tests for the common source identity/capability contract."""

from __future__ import annotations

import pytest

from src.telemetry.collectors.registry import CollectorRegistry, UnsupportedSourceError
from src.telemetry.contracts import SourceStatus, SourceType, capabilities_for
from src.sensors.registry import SensorRegistry


def test_registry_exposes_only_real_supported_sources() -> None:
    registry = CollectorRegistry.default()
    assert SourceType.LOCAL_PACKET_CAPTURE.value in registry.supported_sources()
    assert SourceType.ZEEK.value in registry.supported_sources()
    assert SourceType.REPLAY.value in registry.supported_sources()
    assert SourceType.MOCK.value in registry.supported_sources()
    assert SourceType.NETFLOW.value in registry.registered_sources()
    assert SourceType.IPFIX.value in registry.registered_sources()
    assert SourceType.NETFLOW.value not in registry.supported_sources()
    assert SourceType.IPFIX.value not in registry.supported_sources()


def test_common_collector_contract_supports_bounded_reads() -> None:
    collector = CollectorRegistry.default().create(SourceType.MOCK, events=[{"value": 1}, {"value": 2}])
    collector.start()
    assert collector.read_events(2) == [{"value": 1}, {"value": 2}]
    assert collector.read_events(2) == []
    with pytest.raises(ValueError):
        collector.read_events(0)


def test_capabilities_distinguish_available_and_missing_fields() -> None:
    local = capabilities_for(SourceType.LOCAL_PACKET_CAPTURE)
    zeek = capabilities_for(SourceType.ZEEK)
    assert local.status is SourceStatus.SUPPORTED
    assert local.state_compatible is True
    assert "tcp_flags" in local.available
    assert zeek.status is SourceStatus.PARTIAL
    assert zeek.state_compatible is False
    assert "tcp_flag_counts" in zeek.unavailable
    assert "packet_size_statistics" in zeek.unavailable


def test_netflow_and_ipfix_are_not_claimed_as_supported() -> None:
    registry = CollectorRegistry.default()
    for source in (SourceType.NETFLOW, SourceType.IPFIX):
        with pytest.raises(UnsupportedSourceError, match="not supported"):
            registry.create(source)


def test_unknown_source_is_rejected() -> None:
    with pytest.raises(ValueError):
        capabilities_for("not-a-source")


def test_remote_sensor_detail_exposes_source_identity_without_secrets(tmp_path) -> None:
    registry = SensorRegistry(tmp_path / "registry.json")
    enrollment = registry.create_enrollment()
    registered = registry.register(
        enrollment_token=str(enrollment["enrollment_token"]),
        hostname="agent-01",
        agent_version="0.1.0",
    )
    detail = registry.get(registered["sensor_id"])
    assert detail["source_type"] == "REMOTE_AGENT"
    assert detail["source_status"] == "SUPPORTED"
    assert detail["source_capabilities"]["state_compatible"] is True
    assert "runtime_token" not in detail


def test_remote_sensor_last_event_is_the_latest_state_timestamp(tmp_path) -> None:
    registry = SensorRegistry(tmp_path / "registry.json")
    enrollment = registry.create_enrollment()
    registered = registry.register(
        enrollment_token=str(enrollment["enrollment_token"]),
        hostname="agent-01",
        agent_version="0.1.0",
    )
    registry.accept_telemetry(
        registered["sensor_id"],
        sequence=1,
        batch_hash="a" * 64,
        buffered_item_count=0,
        last_event="2026-09-02T12:00:10+00:00",
    )
    assert registry.get(registered["sensor_id"])["last_event"] == "2026-09-02T12:00:10+00:00"
