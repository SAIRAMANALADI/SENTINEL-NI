# Scapy Capture

## Status: IMPLEMENTED

`LOCAL_PACKET_CAPTURE` is the existing `LiveTelemetryAdapter`, exposed through
the common collector registry as `ScapyCollector`. It uses Scapy's
`AsyncSniffer` with `store=False`, so packet objects and payload bytes are not
retained. The emitted metadata includes the actual capture timestamp, IP
endpoints, ports, protocol, packet length, TCP flags, and available optional
TTL/window/payload-length/fragment information.

Windows requires Npcap with Scapy's pcap backend enabled. Linux requires a
working libpcap installation and the permissions needed by the selected
interface. The existing interface discovery, permission errors, bounded queue,
drop counters, flow builder, and 10-second state path are unchanged.

Start local live mode only with an explicitly configured interface. Docker
containers do not automatically receive the host capture interface; use a
host-native sensor or an explicitly configured capture deployment.
