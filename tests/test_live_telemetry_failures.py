"""Failure and permission handling tests for live telemetry."""

from __future__ import annotations

import pytest

from src.telemetry.live import (
    LIVE_PERMISSION_DENIED,
    LiveTelemetryAdapter,
    LiveTelemetryPermissionDenied,
)


def test_permission_denied_is_reported_without_crashing_adapter() -> None:
    def denied_factory(**_: object) -> object:
        raise PermissionError("capture permission denied")

    adapter = LiveTelemetryAdapter("fixture-interface", sniffer_factory=denied_factory)
    with pytest.raises(LiveTelemetryPermissionDenied):
        adapter.start()
    assert adapter.status()["status"] == LIVE_PERMISSION_DENIED
    assert "permission" in adapter.status()["error"].lower()


def test_capture_backend_error_is_reported() -> None:
    def broken_factory(**_: object) -> object:
        raise OSError("capture backend missing")

    adapter = LiveTelemetryAdapter("fixture-interface", sniffer_factory=broken_factory)
    with pytest.raises(Exception, match="capture backend missing"):
        adapter.start()
    assert adapter.status()["error"] == "capture backend missing"
