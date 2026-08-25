# Supervised State Contract

Status: **AUTHORITATIVE FOR TRAINING AND EVALUATION**  
Schema version: `network-state-v1.0`  
Aggregation interval: **10 seconds**

## Input

The supervised state builder consumes flow rows containing the source fields
listed in `src/features/network_state.py::REQUIRED_COLUMNS`, including
`Label`, `capture_date`, and `timestamp_parsed`. Timestamps must be valid,
belong to their capture day, and timestamp/capture-date anomalies are excluded
under the frozen V1 policy.

`Label` is authoritative only in this supervised path. A flow is considered
malicious when `Label != "Benign"`.

## Output

The output contains:

- `timestamp` and `capture_day` metadata;
- the exact 17 frozen numeric model-input features;
- `malicious_flow_count`;
- `malicious_flow_ratio`;
- `binary_attack_state`;
- `future_attack_state`;
- `future_target_available`.

The target is:

```text
future_attack_state(t) = binary_attack_state(t + 10 seconds)
```

The shift is within the same `capture_day`. Terminal states have
`future_target_available=false` and `future_attack_state=-1`; they are not
usable supervised target rows.

## Model inputs

The 17 model inputs are exactly:

```text
flow_count, byte_sum, packet_sum, mean_duration, median_duration,
mean_iat, iat_std, syn_flow_ratio, ack_flow_ratio, rst_flow_ratio,
fwd_byte_share, fwd_packet_share, unique_destination_port_count,
bytes_per_second, packets_per_second, packet_size_mean, packet_size_std
```

Labels, target columns, timestamps, capture-day identifiers, and provenance are
not input features.

## Boundary

This contract is required for label-derived target construction. It is not the
contract used by live packet inference, where no authoritative label or future
target exists.
