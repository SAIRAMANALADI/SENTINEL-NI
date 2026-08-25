"""Contract tests for live telemetry interface discovery and status shape."""

from __future__ import annotations

from src.telemetry import live


def test_interface_discovery_does_not_start_capture(monkeypatch) -> None:
    class Iface:
        name = "fixture-interface"
        description = "fixture"
        ip = "192.0.2.10"

    class Conf:
        ifaces = {"fixture": Iface()}
        use_pcap = True

    class Backend:
        conf = Conf()

    monkeypatch.setattr(live, "_load_scapy", lambda: Backend)
    interfaces = live.discover_capture_interfaces()
    assert interfaces == [
        {
            "name": "fixture-interface",
            "description": "fixture",
            "address": "192.0.2.10",
            "status": "DISCOVERED",
            "capture_available": True,
        }
    ]


def test_live_status_has_operator_safe_fields() -> None:
    adapter = live.LiveTelemetryAdapter("fixture-interface", sniffer_factory=lambda **_: None)
    status = adapter.status()
    assert {
        "mode",
        "interface",
        "status",
        "started_at",
        "last_event_at",
        "event_count",
        "stale",
    }.issubset(status)
    assert "payload" not in status
    assert "raw_packet" not in status
