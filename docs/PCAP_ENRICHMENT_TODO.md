# PCAP Enrichment TODO

The current network-state artifact is flow-derived only. Do not fill these fields with zeros or estimates.

When matching CSE-CIC-IDS2018 PCAPs are explicitly acquired and joined to the same capture day/machine scope, add a separate versioned enrichment module for:

- packet-level TTL distributions and changes;
- IP fragmentation flags and fragment counts;
- packet-accurate TCP window observations;
- retransmission indicators from sequence/acknowledgement evidence;
- raw packet inter-arrival and burst-order statistics;
- packet payload-size distributions where flow summaries are insufficient;
- packet flag order and handshake evidence; and
- flow-to-PCAP alignment validation.

The current handoff remains valid for flow-derived states, but these PCAP fields are unavailable and are not part of `network-state-v1.0`.
