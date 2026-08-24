# Flow/State Pipeline V1 Freeze

Freeze status: **VERSION 1 FROZEN**
Freeze scope: validated flow ingestion and flow-derived 10-second network states only.

## Dataset

Dataset: CSE-CIC-IDS2018 multi-day flow data.

```text
data/processed/cic_ids2018_multiday_flow.parquet
```

The artifact contains 3,758,796 raw flow rows and 3,758,782 valid temporal rows. Fourteen timestamp/capture-date anomalies are excluded from temporal aggregation without correcting or rewriting the raw records.

## State representation

State artifact:

```text
data/processed/cic_ids2018_network_states.parquet
```

- Schema version: `network-state-v1.0`;
- aggregation interval: **10 seconds**;
- state definition: half-open `[t, t + 10 seconds)` intervals within one `capture_day`;
- empty intervals: retained as explicit zero-traffic states;
- cross-day aggregation: prohibited;
- total states: **16,127**;
- timestamp range: `2018-02-14 01:00:00` through `2018-02-28 12:59:50`;
- capture-day range: `2018-02-14` through `2018-02-28`.

## Frozen model-input features

Exactly 17 flow-derived numeric features are frozen:

```text
flow_count
byte_sum
packet_sum
mean_duration
median_duration
mean_iat
iat_std
syn_flow_ratio
ack_flow_ratio
rst_flow_ratio
fwd_byte_share
fwd_packet_share
unique_destination_port_count
bytes_per_second
packets_per_second
packet_size_mean
packet_size_std
```

Source labels, target metadata, timestamps, capture-day identifiers, and provenance fields are not model inputs.

## Frozen target

For each valid flow:

```text
malicious_flow = 1 if Label != "Benign" else 0
```

For each state:

```text
malicious_flow_count = sum(malicious_flow)
malicious_flow_ratio = malicious_flow_count / flow_count, or 0 for an empty state
binary_attack_state = 1 if malicious_flow_count > 0 else 0
future_attack_state(t) = binary_attack_state(t + 10 seconds)
```

The future shift remains within the same `capture_day`. The final state of each day has `future_target_available=false` and `future_attack_state=-1` and must be excluded from supervised target rows. This is an observed malicious-traffic-presence target, not a claim of compromise or an MITRE mapping.

## Frozen day-aware split

No random row split is permitted.

| Partition | Capture days | States |
|---|---|---:|
| Train | `2018-02-14`, `2018-02-21` | 7,487 |
| Validation | `2018-02-22` | 4,320 |
| Test | `2018-02-28` | 4,320 |

Existing split paths:

```text
data/processed/states/train.parquet
data/processed/states/validation.parquet
data/processed/states/test.parquet
```

## Validation evidence

- 17 model-input features are numeric, with 0 NaN and 0 Inf in the state artifact;
- duplicate `(capture_day, timestamp)` state keys: 0;
- timestamps are chronological within each capture day;
- split days are disjoint and complete-day based;
- latest full test suite: 133 passed; current verification details are recorded in `results/FORENSIC_CLEANUP_REPORT.md`.

## Known packet-level gap and limitations

V1 is flow-derived. It does not contain verified packet-level TTL, fragmentation, retransmission, packet-order/IAT sequences, payload distributions, full TCP-window observations, or TCP flag ordering. The current flow artifact also lacks source/destination IPs, source port, Flow ID, and machine identity, so the 53.25 GB 28-Feb PCAP archive cannot currently be matched safely. No packet features are fabricated or included in V1.

Completed-flow aggregates may include information from a flow’s full duration; V1 is not an intra-flow packet-cutoff early-warning representation. Further packet enrichment requires a separately approved, identity-preserving acquisition and matching plan.
