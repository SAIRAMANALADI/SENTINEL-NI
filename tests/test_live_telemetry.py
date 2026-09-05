"""Unit tests for metadata-only live packet conversion and lifecycle."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import threading
import time

import pytest

from src.telemetry import live


class IP:
    def __init__(self) -> None:
        self.src = "10.0.0.2"
        self.dst = "10.0.0.20"
        self.ttl = 64
        self.frag = 0


class TCP:
    def __init__(self) -> None:
        self.sport = 12345
        self.dport = 443
        self.flags = "S"
        self.window = 4096
        self.payload = b"payload-is-not-retained"


class FakePacket:
    time = 1_700_000_000

    def __init__(self, *, ip: bool = True, tcp: bool = True) -> None:
        self.ip = IP() if ip else None
        self.tcp = TCP() if tcp else None

    def haslayer(self, layer: object) -> bool:
        return (layer is IP and self.ip is not None) or (layer is TCP and self.tcp is not None)

    def __getitem__(self, layer: object) -> object:
        if layer is IP:
            return self.ip
        if layer is TCP:
            return self.tcp
        raise KeyError(layer)

    def __len__(self) -> int:
        return 128


class FakeScapy:
    IP = IP
    IPv6 = type("IPv6", (), {})
    TCP = TCP
    UDP = type("UDP", (), {})
    ICMP = type("ICMP", (), {})


class FakeSniffer:
    def __init__(self, *, prn, **_: object) -> None:
        self.prn = prn
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True
        self.prn(FakePacket())

    def stop(self) -> None:
        self.stopped = True


def test_valid_packet_conversion_preserves_required_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(live, "_load_scapy", lambda: FakeScapy)
    event = live.packet_to_event(FakePacket(), scapy=FakeScapy)
    assert event["source_ip"] == "10.0.0.2"
    assert event["destination_port"] == 443
    assert event["protocol"] == "TCP"
    assert event["packet_length"] == 128
    assert event["tcp_flags"] == "S"
    assert event["ttl"] == 64
    assert event["tcp_window"] == 4096
    assert "payload" not in event
    assert event["payload_length"] == len(b"payload-is-not-retained")


def test_unsupported_packet_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(live, "_load_scapy", lambda: FakeScapy)
    with pytest.raises(live.UnsupportedPacket):
        live.packet_to_event(FakePacket(ip=False), scapy=FakeScapy)


def test_start_read_stop_and_status(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(live, "packet_to_event", lambda packet: {"timestamp": "2026-01-01T00:00:00+00:00"})
    adapter = live.LiveTelemetryAdapter("test-interface", sniffer_factory=FakeSniffer)
    assert adapter.status()["status"] == live.LIVE_STOPPED
    adapter.start()
    assert adapter.status()["status"] == live.LIVE_RUNNING
    assert adapter.status()["event_count"] == 1
    assert adapter.read_event()["timestamp"] == "2026-01-01T00:00:00+00:00"
    adapter.stop()
    assert adapter.status()["status"] == live.LIVE_STOPPED


def test_concurrent_start_creates_only_one_sniffer(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(live, "packet_to_event", lambda packet: {"timestamp": "2026-01-01T00:00:00+00:00"})
    created: list[FakeSniffer] = []
    created_lock = threading.Lock()

    def slow_factory(**kwargs: object) -> FakeSniffer:
        time.sleep(0.05)
        sniffer = FakeSniffer(**kwargs)
        with created_lock:
            created.append(sniffer)
        return sniffer

    adapter = live.LiveTelemetryAdapter("test-interface", sniffer_factory=slow_factory)
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(lambda _: adapter.start(), range(2))) == [None, None]

    assert len(created) == 1
    adapter.stop()
    assert created[0].stopped is True


def test_missing_interface_is_unavailable() -> None:
    adapter = live.LiveTelemetryAdapter(None, sniffer_factory=FakeSniffer)
    assert adapter.status()["status"] == live.LIVE_UNAVAILABLE
    with pytest.raises(live.LiveTelemetryUnavailable):
        adapter.start()


def test_stale_status_is_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(live, "packet_to_event", lambda packet: {"timestamp": "2026-01-01T00:00:00+00:00"})
    adapter = live.LiveTelemetryAdapter("test-interface", stale_after_seconds=5, sniffer_factory=FakeSniffer)
    adapter.start()
    adapter._started_at = datetime.now(timezone.utc) - timedelta(seconds=10)
    assert adapter.status()["stale"] is True


def test_callback_mode_does_not_fill_unused_read_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(live, "packet_to_event", lambda packet: {"timestamp": "2026-01-01T00:00:00+00:00"})
    delivered: list[dict[str, object]] = []
    adapter = live.LiveTelemetryAdapter(
        "test-interface",
        sniffer_factory=FakeSniffer,
        event_callback=delivered.append,
        queue_size=1,
    )

    adapter._on_packet(object())
    adapter._on_packet(object())

    assert len(delivered) == 2
    assert adapter.read_event() is None
    assert adapter.status()["dropped_count"] == 0


def test_callback_failure_is_a_delivery_drop_not_a_parse_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(live, "packet_to_event", lambda packet: {"timestamp": "2026-01-01T00:00:00+00:00"})

    def reject(_: dict[str, object]) -> None:
        raise RuntimeError("runtime unavailable")

    adapter = live.LiveTelemetryAdapter(
        "test-interface",
        sniffer_factory=FakeSniffer,
        event_callback=reject,
    )
    adapter._on_packet(object())

    status = adapter.status()
    assert status["dropped_count"] == 1
    assert status["callback_error_count"] == 1
    assert status["parse_error_count"] == 0


def test_callback_rejection_is_counted_as_a_drop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(live, "packet_to_event", lambda packet: {"timestamp": "2026-01-01T00:00:00+00:00"})
    adapter = live.LiveTelemetryAdapter(
        "test-interface",
        sniffer_factory=FakeSniffer,
        event_callback=lambda event: False,
    )

    adapter._on_packet(object())

    status = adapter.status()
    assert status["dropped_count"] == 1
    assert status["callback_rejected_count"] == 1
    assert status["callback_error_count"] == 0
