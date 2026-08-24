# ML Freeze Contract

Status: **READY FOR NIKHIL using the frozen flow/state V1 artifact.**

This contract freezes the data/network interface. It does not authorize model training in this task and does not include packet enrichment.

## Input

`data/processed/cic_ids2018_network_states.parquet`

Schema version: `network-state-v1.0`
Aggregation interval: **10 seconds**
State count: **16,127**

## Features

Nikhil may use exactly these 17 state features as model inputs:

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

Do not use `Label`, `original_label`, `source_file`, `capture_date`, `timestamp`, `capture_day`, or any target column as a model feature. No packet feature is part of this contract.

## Target

The approved one-step target is:

`future_attack_state(t) = binary_attack_state(t + 10 seconds)`

The shift is within the same `capture_day`. `binary_attack_state` is 1 when the current state contains at least one source flow whose `Label` is not `Benign`, otherwise 0. The final state per day has `future_target_available=false` and `future_attack_state=-1`; filter unavailable targets before supervised training.

## Splits

Use the existing complete-day, non-random split:

| Partition | Exact path | Capture day(s) | States |
|---|---|---|---:|
| Train | `data/processed/states/train.parquet` | `2018-02-14`, `2018-02-21` | 7,487 |
| Validation | `data/processed/states/validation.parquet` | `2018-02-22` | 4,320 |
| Test | `data/processed/states/test.parquet` | `2018-02-28` | 4,320 |

Do not randomly split rows, mix capture days across partitions, or create windows that cross a partition boundary.

## Guarantees

- model-input features are numeric;
- state model-input features contain no NaN or Inf;
- target columns are separate from model inputs;
- timestamps are chronological within each capture day;
- state construction does not cross capture-day boundaries;
- train, validation, and test capture days are disjoint;
- 14 malformed timestamp rows were excluded from temporal aggregation and preserved in the flow artifact;
- packet-level features are not present and must not be inferred from V1.

## Ownership boundary

Project Lead owns this data/network contract, source data, state construction, target definition, and split integrity. Nikhil owns temporal windows, baseline/model code, forecasting, evaluation, and inference. Any change to the input features, target, interval, or split requires a new contract version and Project Lead review.
