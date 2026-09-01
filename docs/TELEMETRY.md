# Telemetry Sources

The adapter boundary is `src/telemetry/base.py`. Current implementations are:

- `LiveTelemetryAdapter`: Scapy/Npcap/libpcap packet metadata from one host
  interface.
- `ReplayTelemetryAdapter`: deterministic file-backed events for development,
  CI, and troubleshooting.
- `MockTelemetryAdapter`: deterministic unit-test input.

The live adapter converts packets to validated metadata such as endpoints,
ports, protocol, packet length, TCP flags, TTL, TCP window, fragment state,
and payload length. Packet objects and payload bytes are not retained.

Malformed or unsupported packets are counted and discarded. The live event
queue is bounded and status exposes accepted, ignored, rejected, dropped, and
stale signals. Capture failures are reported through explicit API status and
do not silently become a healthy forecast.

Future Zeek, tshark, NetFlow, or IPFIX adapters should implement the same
metadata contract. They must not bypass flow validation or fabricate fields
that their source does not provide.
