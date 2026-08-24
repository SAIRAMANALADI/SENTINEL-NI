# Network State Specification

Schema version: `network-state-v1.0`
Selected interval: **10 seconds**

## Definition

`S_t` is the aggregate of valid completed flow records whose parsed flow timestamp falls in the half-open interval:

```text
[t, t + 10 seconds)
```

Intervals are generated independently inside each `capture_day`, from that day’s valid observed minimum to maximum interval. Empty intervals are retained as explicit zero-traffic states. No interval crosses a capture-day boundary. The 14 timestamp/capture-date anomalies are excluded from temporal aggregation under the policy in `results/TIMESTAMP_ANOMALY_FINAL_DECISION.md`.

## Feature inputs

The model-input feature list is authoritative in `configs/state_feature_schema.yaml`:

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

All are derived only from flow fields present in the verified artifact. `mean_duration`, `mean_iat`, and packet-size fields retain the source export’s units; they are not silently reinterpreted. `bytes_per_second` and `packets_per_second` are state sums divided by 10 seconds.

Source/destination IP fan-out is not included because those fields are absent from this CSV. TTL, fragmentation, retransmission evidence, packet-order IATs, and packet-accurate payload features require PCAP and are not fabricated.

## Feature formulas

| Feature | Source fields | Formula/aggregation | Type/unit | Leakage risk |
|---|---|---|---|---|
| `flow_count` | flow rows | count of valid flows in interval | int / flows | low |
| `byte_sum` | `TotLen Fwd Pkts`, `TotLen Bwd Pkts` | sum of forward plus backward bytes | float / source bytes | low |
| `packet_sum` | `Tot Fwd Pkts`, `Tot Bwd Pkts` | sum of forward plus backward packets | float / packets | low |
| `mean_duration` | `Flow Duration` | mean across flows | float / source units | low |
| `median_duration` | `Flow Duration` | median across flows | float / source units | low |
| `mean_iat` | `Flow IAT Mean` | mean of flow-level IAT means | float / source units | low |
| `iat_std` | `Flow IAT Std` | mean of flow-level IAT standard deviations | float / source units | low |
| `syn_flow_ratio` | `SYN Flag Cnt` | fraction of flows with SYN count > 0 | float / proportion | low |
| `ack_flow_ratio` | `ACK Flag Cnt` | fraction of flows with ACK count > 0 | float / proportion | low |
| `rst_flow_ratio` | `RST Flag Cnt` | fraction of flows with RST count > 0 | float / proportion | low |
| `fwd_byte_share` | directional byte fields | forward bytes / total bytes; zero when total is zero | float / proportion | low |
| `fwd_packet_share` | directional packet fields | forward packets / total packets; zero when total is zero | float / proportion | low |
| `unique_destination_port_count` | `Dst Port` | distinct destination ports in interval | int / ports | medium; retain for later leakage review |
| `bytes_per_second` | `byte_sum` | byte sum / 10 | float / bytes per second | low |
| `packets_per_second` | `packet_sum` | packet sum / 10 | float / packets per second | low |
| `packet_size_mean` | `Pkt Len Mean` | mean of flow-level packet-length means | float / source units | low |
| `packet_size_std` | `Pkt Len Std` | mean of flow-level packet-length standard deviations | float / source units | low |

The source `Label`, `original_label`, binary targets, timestamps, capture-day identifiers, and provenance fields are not model-input features.

## Measured interval choice

All candidate intervals were measured in `results/TEMPORAL_GRANULARITY_COMPARISON.md`. The 10-second choice retains `16,127` states, has `34.35%` empty states, and preserves more temporal resolution than 30/60 seconds without the larger sparse table produced by 1 second. This is an engineering representation choice, not a model-performance claim.
