# Project Lead to Nikhil: Network-State Handoff

Date: 2026-08-24
Status: **NETWORK STATE READY FOR NIKHIL**

## Scope completed

The flow-derived network-state layer is finalized for the current four-day CSE-CIC-IDS2018 artifact. This handoff stops before supervised model training, sequence-window generation, inference, or evaluation.

Input artifact:

```text
data/processed/cic_ids2018_multiday_flow.parquet
```

Output artifact:

```text
data/processed/cic_ids2018_network_states.parquet
```

The selected fixed interval is **10 seconds**. States are built independently within each capture day and empty intervals are retained. The state table contains **16,127 states** from **3,758,782 valid flows**.

## Model-input features

The authoritative schema is `configs/state_feature_schema.yaml`. It contains 17 numeric flow-derived features:

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

`Label`, `original_label`, `malicious_flow_count`, `malicious_flow_ratio`, `binary_attack_state`, `future_attack_state`, `timestamp`, `capture_day`, and provenance fields are not model-input features.

## Target definition

The current state target is observed malicious-traffic presence:

```text
malicious_flow = 1 if source Label != Benign else 0
binary_attack_state = 1 if the current 10-second state contains at least one malicious flow else 0
```

The one-step forecasting target is:

```text
future_attack_state(t) = binary_attack_state(t + 10 seconds)
```

The shift is performed only within the same `capture_day`. The final state of each day has `future_target_available=false` and `future_attack_state=-1`; modeling code must filter it out. This is an observed dataset-label target, not a claim of compromise, attack stage, or MITRE ATT&CK mapping.

## Day-aware split

The split is complete-day and chronological; no rows or states were randomly distributed across partitions:

| Partition | Capture days | States | Future target available | Future 0 | Future 1 |
|---|---|---:|---:|---:|---:|
| Train | 2018-02-14, 2018-02-21 | 7,487 | 7,485 | 6,080 | 1,405 |
| Validation | 2018-02-22 | 4,320 | 4,319 | 4,155 | 164 |
| Test | 2018-02-28 | 4,320 | 4,319 | 3,521 | 798 |

Split artifacts:

```text
data/processed/states/train.parquet
data/processed/states/validation.parquet
data/processed/states/test.parquet
results/network_state_split_report.json
```

The test day contains the `Infilteration` source label pattern, which is absent from the earlier training days. Source-label summaries remain in the flow-level reports; state targets use the documented binary presence rule.

## Timestamp decision

Fourteen flow rows parse to January 1970 despite belonging to the 2018-02-14 or 2018-02-22 source files. There is no alternate date field to correct them reliably. Per `results/TIMESTAMP_ANOMALY_FINAL_DECISION.md`, these 14 rows are excluded from temporal aggregation without changing the raw flow artifact. No timestamps or packet features were fabricated.

## PCAP-only gaps

The current state table is flow-derived. It does not claim to provide:

- packet-order timing or packet-level IAT reconstruction;
- TTL and hop-distance behavior;
- IP fragmentation indicators;
- retransmission evidence;
- packet payload-size distributions beyond the source flow exporter fields;
- payload/content or protocol-state inspection;
- source/destination IP fan-out, because IP fields are absent from the current canonical artifact.

These belong in the separate `docs/PCAP_ENRICHMENT_TODO.md` module and must not be backfilled with synthetic values.

## Files to read

```text
docs/NETWORK_STATE_SPEC.md
docs/TARGET_STATE_SPEC.md
configs/state_feature_schema.yaml
results/TEMPORAL_GRANULARITY_COMPARISON.md
results/TIMESTAMP_ANOMALY_FINAL_DECISION.md
results/network_state_split_report.json
```

## Exact next engineering action

Nikhil should validate the three split Parquet files against `configs/state_feature_schema.yaml`, filter to `future_target_available == true`, and then implement sequence-window construction using only the 17 listed features. Do not train a model in this handoff step.

Validation command:

```powershell
python scripts/build_state_splits.py --input data/processed/cic_ids2018_network_states.parquet --split-report results/multiday_split_report.json
```

The aggregation and split tests are part of the repository test suite. Current verification result: **32 passed**.
