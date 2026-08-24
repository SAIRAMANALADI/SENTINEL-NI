# PCAP Feature Gap

Date: 2026-08-24  
Source audited: CSE-CIC-IDS2018 flow CSV only

The flow CSV provides aggregate directional flow features, but it does not satisfy the packet-level requirements. No PCAP was downloaded or parsed in this task.

| Requirement | Available from CSV? | Why | Future PCAP extraction plan |
|---|---|---|---|
| TTL | No | No TTL column is present. | Read IP TTL per packet and emit directional/window distributions. |
| Fragmentation | No | No fragment flags, fragment offsets, or IP identification fields are present. | Read IP fragmentation fields and count fragmented/reassembled traffic. |
| Retransmissions | No | No TCP sequence/acknowledgement or retransmission indicator is present. | Detect sequence retransmissions from packet headers, with direction-aware flow joins. |
| Packet-level IAT / burst ordering | No | CSV contains only aggregate IAT summaries. | Preserve packet timestamps, calculate packet IAT sequences and burst statistics. |
| Packet payload distributions | Partial only | Packet/segment length summaries exist, but no raw payload-length distribution is available. | Read captured packet payload lengths and emit exact distributions/quantiles. |
| Complete TCP window observations | Partial only | `Init Fwd Win Byts` and `Init Bwd Win Byts` are initial values only. | Read TCP advertised-window values across packets and aggregate by flow/window. |
| Packet flag order | No | Flow-level flag counts do not preserve packet order or handshake transitions. | Extract per-packet TCP flags and ordered handshake/termination events. |
| Source IP / destination IP | No | The CSV has only `Dst Port` and `Protocol` among flow-key fields. | Extract IP endpoints from PCAP and apply the approved privacy/retention policy. |
| Source port | No | No source-port column is present. | Extract source ports and validate five-tuple directionality. |
| Full flow identifiers | No | No `Flow ID`, source IP, destination IP, or source port is present. | Reconstruct five-tuples plus timestamps and validate flow-to-CSV matching. |

The PCAP module must report unavailable fields explicitly if the matching capture does not expose them. It must not synthesize packet-level values from flow aggregates.
