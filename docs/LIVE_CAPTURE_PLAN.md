# Future Live Capture Plan

Live capture is not implemented. Any future adapter must emit the same `ReplayEvent`/state contract used by offline replay and must not bypass the frozen 10-second state validator.

| Source | Input | Deployment point | Permissions | Packet visibility | Aggregation integration | Limitations |
|---|---|---|---|---|---|---|
| Scapy/libpcap | Local interface packets or a capture file | Sensor host or test workstation | Raw-socket/admin privileges commonly required | Packet headers and payload visibility depend on capture permissions | Adapt packets to flow events, then reuse the state aggregator | Python overhead, dropped packets, platform permissions, and incomplete identity matching risk |
| Zeek | Zeek flow/log/event output from a monitored interface | Dedicated sensor or network tap | Sensor deployment and interface/tap access | Strong structured metadata; payload visibility depends on configuration | Map Zeek records to the common event contract | Schema mapping, clock alignment, and deployment overhead |
| tshark | Live interface or rotating PCAP capture | Sensor host or capture appliance | Interface/capture permissions | Rich dissector fields subject to capture visibility | Convert selected records to common flow events | Process supervision, output back-pressure, versioned field names, and storage management |

The current CSE-CIC-IDS2018 flow artifact does not provide enough canonical identity to justify a flow-to-PCAP join. That gap remains a prerequisite for any packet-enriched production path.
