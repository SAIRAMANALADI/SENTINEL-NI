# PCAP Gap and Next Strategy

Status: **PCAP enrichment remains blocked; Flow/State V1 is the active contract.**

## A. Packet-level requirements in the project contract

The repository’s SIH/network-intelligence contract calls for packet evidence for:

- IP TTL observations;
- IP fragmentation indicators;
- retransmission detection;
- packet-level inter-arrival timing and burst/order behavior;
- packet payload-size distributions;
- TCP advertised-window observations;
- ordered TCP flag/handshake behavior;
- packet counts and packet timing statistics;
- defensible packet-to-flow or packet-to-state association.

The official SIH problem statement is not present in the repository, so this list is treated as the project’s documented provisional requirement contract, not as a newly verified quotation from the official statement.

## B. What V1 already represents or approximates

The current CICFlowMeter-derived flow data provides flow-level proxies that are retained in V1:

| Packet-oriented need | V1 representation | Classification |
|---|---|---|
| Packet counts | `packet_sum` from directional flow packet counts | Flow aggregate proxy |
| Byte/payload size | `byte_sum`, `packet_size_mean`, `packet_size_std`, directional byte shares | Flow/exporter aggregate proxy |
| Timing | `mean_iat`, `iat_std`, `mean_duration`, rate features | Flow aggregate proxy |
| TCP flags | `syn_flow_ratio`, `ack_flow_ratio`, `rst_flow_ratio` | Presence/count proxy, not order |
| TCP window | None in state inputs | Initial-window source fields are not packet observations |
| Destination behavior | `unique_destination_port_count` | Flow-state port diversity only |

These proxies must not be described as packet-level extraction. V1 contains no raw packet records and no packet-derived columns.

## C. Genuinely unavailable requirements

The following are unavailable in V1 and must remain unavailable until real matching packet evidence is obtained:

- per-packet TTL distributions;
- fragment flags, offsets, IDs, and reassembly evidence;
- reliable sequence/acknowledgement retransmission detection;
- ordered packet timestamps, packet IAT sequences, and burst transitions;
- packet-accurate payload-length distributions;
- all-packet TCP window observations;
- ordered TCP flag transitions and handshake/termination sequences;
- packet-level source/destination identity needed for a five-tuple join.

No zero-filling, flow-proxy relabeling, or synthetic packet values are allowed.

## D. Why the current CIC archive cannot be matched safely

The documented 28-Feb source is:

```text
s3://cse-cic-ids2018/Original Network Traffic and Log data/Wednesday-28-02-2018/pcap.zip
```

It is approximately 53.25 GB compressed and contains hundreds of machine captures. S3 byte-range access exists, but the current canonical flow artifact contains only timestamp, destination port, and protocol among the usable matching fields. It lacks source/destination IP, source port, Flow ID, and machine/capture identity.

Timestamp + destination port + protocol is collision-prone across concurrent machines and connections. No timestamp tolerance between completed CICFlowMeter flows and packet events has been measured. Selecting a small archive member by guess would create an unverified scope mismatch. Therefore no archive download, packet parse, flow join, or packet feature implementation is approved.

## E. Alternative strategies to research

These are research options, not approved changes to V1:

1. Obtain a per-machine/per-day flow export retaining the canonical five-tuple, exporter flow ID, and capture provenance, then match only the corresponding PCAP member.
2. Use CIC event logs, attack schedules, and machine inventory to establish an auditable machine/IP subset before requesting a bounded PCAP extraction; require a hash and capture-scope manifest.
3. Ask for or acquire an already-extracted 28-Feb infiltration subset whose PCAP and flow CSV share the same machine and time scope; verify headers and timestamps before processing.
4. Research whether the public object store exposes individual machine captures as independently addressable objects or only as ZIP members; do not assume ZIP-member range extraction is sufficient without local-header and integrity validation.
5. Evaluate a smaller public packet/flow dataset with explicit five-tuple alignment as a separate benchmark, without merging it into the CIC V1 state dataset or changing the target.

Any future route must document source identity, exact object/member, capture-day and machine scope, timestamp semantics/tolerance, collision policy, checksums, and matched/unmatched counts before packet features are admitted.
