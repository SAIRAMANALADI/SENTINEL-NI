# Source Attribution Specification

## Status

This is a **prototype input-adapter contract** for deterministic replay and future live packet/event streams. It has not been validated against the CSE-CIC-IDS2018 PCAP archive because the authoritative PCAP-to-flow mapping remains unverified.

## Identity

The observed flow identity is:

```text
flow_5tuple = (
  source_ip,
  destination_ip,
  source_port,
  destination_port,
  protocol
)
```

The source grouping key is:

```text
source_key = source_ip
```

`source_ip` identifies an observed network endpoint in the event stream. It does not necessarily identify a human user, process, organization, or attacker.

The system therefore uses **suspicious source** or **candidate source**, never **attacker**, unless separate evidence supports that attribution.

## Reverse-flow handling

The observed `flow_5tuple` preserves packet direction. For flow counting, the adapter also constructs a direction-independent canonical key by ordering the two `(IP, port)` endpoints. Forward and reverse packets therefore contribute to one canonical flow count, while source activity remains attributed to the observed `source_ip` on each packet.

No five-tuple is reconstructed from the current CSE-CIC-IDS2018 combined flow artifact. The fields are accepted only when supplied by a real packet/event source.

## Packet event contract

Required fields are defined in `configs/packet_event_schema.yaml`:

- `timestamp`
- `source_ip`
- `destination_ip`
- `source_port`
- `destination_port`
- `protocol`
- `packet_length`
- `tcp_flags`

Optional fields are accepted only when present in the input:

- `ttl`
- `ip_fragment`
- `tcp_window`
- `payload_length`

The current aggregator does not synthesize or infer optional fields.

## Aggregation

Observed events are grouped into fixed 10-second intervals and source IPs. The activity table contains:

`flow_count`, `packet_count`, `byte_count`, `unique_destinations`, `unique_destination_ports`, `mean_packet_size`, `mean_iat`, `syn_count`, `ack_count`, and `rst_count`, plus deterministic packet/byte rates and interval boundaries.

Duplicate input rows are retained as observed packets because the minimum schema has no packet identifier or approved deduplication rule. Batch aggregation stably sorts out-of-order events; streaming replay requires chronological events.

## Non-claims

- A source priority is not a probability.
- A high-priority source is not a confirmed attacker.
- Network forecast context is not source attribution.
- The prototype does not automatically block traffic.
- The prototype has no CSE-CIC-IDS2018 PCAP validation result.
