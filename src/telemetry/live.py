"""Optional live packet metadata adapter backed by Scapy.

The adapter deliberately emits only the approved packet-event metadata
contract.  It never stores packet objects or payload bytes.
"""

from __future__ import annotations

from datetime import datetime, timezone
import os
from queue import Empty, Full, Queue
from threading import Lock
from collections import Counter
from typing import Any, Callable

from src.telemetry.base import TelemetryAdapter


LIVE_READY = "LIVE_READY"
LIVE_RUNNING = "LIVE_RUNNING"
LIVE_STOPPED = "LIVE_STOPPED"
LIVE_UNAVAILABLE = "LIVE_UNAVAILABLE"
LIVE_PERMISSION_DENIED = "LIVE_PERMISSION_DENIED"
LIVE_ERROR = "LIVE_ERROR"


class LiveTelemetryError(RuntimeError):
    """Base error for live capture setup and packet conversion."""


class LiveTelemetryUnavailable(LiveTelemetryError):
    """The capture backend or requested interface is unavailable."""


class LiveTelemetryPermissionDenied(LiveTelemetryError):
    """The operating system denied capture access."""


class UnsupportedPacket(LiveTelemetryError):
    """A captured packet is not an IP packet supported by the event contract."""


def _parse_error_category(exc: BaseException) -> str:
    """Classify an ignored capture observation without retaining packet data."""

    message = str(exc).lower()
    if isinstance(exc, UnsupportedPacket) or "not ipv4 or ipv6" in message:
        return "non_ip"
    if "missing endpoints" in message or "no capture timestamp" in message:
        return "malformed_metadata"
    if "unsupported" in message or "protocol" in message:
        return "unsupported_protocol"
    if "port" in message:
        return "missing_ports"
    return "parser_error"


def _load_scapy() -> Any:
    try:
        from scapy import all as scapy_all
    except ImportError as exc:
        raise LiveTelemetryUnavailable(
            "Scapy is not installed; install requirements and configure Npcap/libpcap"
        ) from exc
    return scapy_all


def discover_capture_interfaces() -> list[dict[str, Any]]:
    """List interfaces exposed by Scapy without opening a capture."""

    scapy = _load_scapy()
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    try:
        interfaces = list(scapy.conf.ifaces.values())
    except Exception as exc:  # pragma: no cover - backend-specific failure
        raise LiveTelemetryUnavailable(f"capture interface discovery failed: {exc}") from exc
    provider_available = not (os.name == "nt" and not bool(getattr(scapy.conf, "use_pcap", False)))
    for interface in interfaces:
        name = str(getattr(interface, "name", "") or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        rows.append(
            {
                "name": name,
                "description": str(getattr(interface, "description", "") or ""),
                "address": str(getattr(interface, "ip", "") or ""),
                "status": "DISCOVERED" if provider_available else "BACKEND_UNAVAILABLE",
                "capture_available": provider_available,
            }
        )
    return rows


def _timestamp_from_packet(packet: Any) -> str:
    value = getattr(packet, "time", None)
    if value is None:
        raise LiveTelemetryError("packet has no capture timestamp")
    return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat()


def packet_to_event(packet: Any, *, scapy: Any | None = None) -> dict[str, Any]:
    """Convert one Scapy packet to the approved metadata-only event schema."""

    scapy = scapy or _load_scapy()
    if not hasattr(packet, "haslayer") or not packet.haslayer(scapy.IP) and not packet.haslayer(scapy.IPv6):
        raise UnsupportedPacket("packet is not IPv4 or IPv6")

    ip_layer = packet[scapy.IP] if packet.haslayer(scapy.IP) else packet[scapy.IPv6]
    source_ip = str(ip_layer.src)
    destination_ip = str(ip_layer.dst)
    if not source_ip or not destination_ip:
        raise LiveTelemetryError("IP packet is missing endpoints")

    protocol = "IP"
    source_port = 0
    destination_port = 0
    tcp_flags = ""
    optional: dict[str, Any] = {}
    if packet.haslayer(scapy.TCP):
        tcp = packet[scapy.TCP]
        protocol = "TCP"
        source_port = int(tcp.sport)
        destination_port = int(tcp.dport)
        tcp_flags = str(tcp.flags)
        optional["tcp_window"] = int(tcp.window)
        optional["payload_length"] = int(len(tcp.payload))
    elif packet.haslayer(scapy.UDP):
        udp = packet[scapy.UDP]
        protocol = "UDP"
        source_port = int(udp.sport)
        destination_port = int(udp.dport)
        optional["payload_length"] = int(len(udp.payload))
    elif packet.haslayer(scapy.ICMP):
        protocol = "ICMP"
    elif hasattr(scapy, "ICMPv6EchoRequest") and packet.haslayer(scapy.ICMPv6EchoRequest):
        protocol = "ICMPv6"
    else:
        protocol_number = getattr(ip_layer, "nh", None) if packet.haslayer(scapy.IPv6) else getattr(ip_layer, "proto", None)
        protocol = str(protocol_number) if protocol_number is not None else protocol

    if hasattr(ip_layer, "ttl"):
        optional["ttl"] = int(ip_layer.ttl)
    if hasattr(ip_layer, "frag"):
        optional["ip_fragment"] = bool(int(ip_layer.frag) > 0)
    packet_length = int(len(packet))
    if packet_length < 0:
        raise LiveTelemetryError("packet length is invalid")
    return {
        "timestamp": _timestamp_from_packet(packet),
        "source_ip": source_ip,
        "destination_ip": destination_ip,
        "source_port": source_port,
        "destination_port": destination_port,
        "protocol": protocol,
        "packet_length": packet_length,
        "tcp_flags": tcp_flags,
        **optional,
    }


class LiveTelemetryAdapter(TelemetryAdapter):
    """Explicitly started, bounded-queue live packet adapter."""

    def __init__(
        self,
        interface: str | None,
        *,
        stale_after_seconds: int = 30,
        sniffer_factory: Callable[..., Any] | None = None,
        event_callback: Callable[[dict[str, Any]], None] | None = None,
        queue_size: int = 10_000,
    ) -> None:
        if isinstance(stale_after_seconds, bool) or stale_after_seconds <= 0:
            raise ValueError("stale_after_seconds must be positive")
        if isinstance(queue_size, bool) or queue_size < 1:
            raise ValueError("queue_size must be positive")
        self.interface = interface.strip() if interface else ""
        self.stale_after_seconds = stale_after_seconds
        self._sniffer_factory = sniffer_factory
        self._event_callback = event_callback
        self._queue: Queue[dict[str, Any]] = Queue(maxsize=queue_size)
        self._lock = Lock()
        self._sniffer: Any | None = None
        self._started_at: datetime | None = None
        self._last_event_at: datetime | None = None
        self._event_count = 0
        self._dropped_count = 0
        self._parse_error_count = 0
        self._parse_error_categories: Counter[str] = Counter()
        self._error: str | None = None
        self._state = LIVE_STOPPED
        self._backend_available = True
        if not self.interface:
            self._backend_available = False
            self._error = "live telemetry requires SIH_TELEMETRY_INTERFACE"
            self._state = LIVE_UNAVAILABLE
        if self._sniffer_factory is None:
            try:
                _load_scapy()
            except LiveTelemetryUnavailable as exc:
                self._backend_available = False
                self._error = str(exc)
                self._state = LIVE_UNAVAILABLE

    def _set_error(self, message: str, state: str = LIVE_ERROR) -> None:
        with self._lock:
            self._error = message
            self._state = state

    def _on_packet(self, packet: Any) -> None:
        try:
            event = packet_to_event(packet)
        except (LiveTelemetryError, ValueError, TypeError) as exc:
            with self._lock:
                self._parse_error_count += 1
                self._parse_error_categories[_parse_error_category(exc)] += 1
            return
        with self._lock:
            self._event_count += 1
            self._last_event_at = datetime.now(timezone.utc)
        try:
            self._queue.put_nowait(event)
        except Full:
            with self._lock:
                self._dropped_count += 1
        if self._event_callback is not None:
            try:
                self._event_callback(dict(event))
            except Exception:
                with self._lock:
                    self._parse_error_count += 1
                    self._parse_error_categories["callback_error"] += 1

    def start(self) -> None:
        with self._lock:
            if self._state == LIVE_RUNNING:
                return
            if not self._backend_available:
                raise LiveTelemetryUnavailable(self._error or "capture backend unavailable")
        try:
            if self._sniffer_factory is None:
                scapy = _load_scapy()
                if os.name == "nt" and not bool(getattr(scapy.conf, "use_pcap", False)):
                    message = "Npcap/libpcap is not available to Scapy on this Windows host"
                    self._set_error(message, LIVE_UNAVAILABLE)
                    raise LiveTelemetryUnavailable(message)
                available = {row["name"] for row in discover_capture_interfaces()}
                if self.interface not in available:
                    raise LiveTelemetryUnavailable(f"capture interface not found: {self.interface}")
                factory = scapy.AsyncSniffer
            else:
                factory = self._sniffer_factory
            self._sniffer = factory(iface=self.interface, prn=self._on_packet, store=False)
            self._sniffer.start()
        except PermissionError as exc:
            self._set_error(str(exc), LIVE_PERMISSION_DENIED)
            raise LiveTelemetryPermissionDenied(str(exc)) from exc
        except LiveTelemetryError:
            raise
        except OSError as exc:
            message = str(exc)
            state = LIVE_PERMISSION_DENIED if "permission" in message.lower() or "access" in message.lower() else LIVE_ERROR
            self._set_error(message, state)
            if state == LIVE_PERMISSION_DENIED:
                raise LiveTelemetryPermissionDenied(message) from exc
            raise LiveTelemetryError(message) from exc
        except Exception as exc:
            self._set_error(str(exc), LIVE_ERROR)
            raise LiveTelemetryError(str(exc)) from exc
        with self._lock:
            self._started_at = datetime.now(timezone.utc)
            self._last_event_at = None
            self._error = None
            self._state = LIVE_RUNNING

    def stop(self) -> None:
        sniffer = self._sniffer
        self._sniffer = None
        if sniffer is not None:
            try:
                sniffer.stop()
            except Exception as exc:  # pragma: no cover - backend-specific failure
                self._set_error(str(exc), LIVE_ERROR)
                return
        with self._lock:
            if self._state != LIVE_UNAVAILABLE:
                self._state = LIVE_STOPPED

    def read_event(self) -> dict[str, Any] | None:
        try:
            return self._queue.get_nowait()
        except Empty:
            return None

    def status(self) -> dict[str, Any]:
        with self._lock:
            stale = False
            if self._state == LIVE_RUNNING:
                reference = self._last_event_at or self._started_at
                stale = reference is None or (datetime.now(timezone.utc) - reference).total_seconds() > self.stale_after_seconds
            return {
                "adapter": "live",
                "mode": "live",
                "interface": self.interface,
                "status": self._state,
                "available": self._backend_available and self._state not in {LIVE_UNAVAILABLE, LIVE_ERROR},
                "started_at": self._started_at.isoformat() if self._started_at else None,
                "last_event_at": self._last_event_at.isoformat() if self._last_event_at else None,
                "event_count": self._event_count,
                "dropped_count": self._dropped_count,
                "parse_error_count": self._parse_error_count,
                "parse_error_categories": dict(self._parse_error_categories),
                "stale": stale,
                "error": self._error,
            }
