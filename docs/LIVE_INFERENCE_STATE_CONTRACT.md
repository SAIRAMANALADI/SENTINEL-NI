# Live Inference State Contract

Status: **READY FOR LABEL-FREE LIVE STATE GENERATION**  
Schema version: `network-state-v1.0`  
Aggregation interval: **10 seconds**

## Purpose

Live inference needs the same 17 numeric inputs used by the frozen model. It
does not need a training label and it cannot create a future target from the
current packet stream. This is an expected contract distinction, not an
error.

## Input

The inference entry point is:

```python
from src.features.network_state import build_network_state_for_inference
```

It accepts completed live flow records with the fields in
`INFERENCE_REQUIRED_COLUMNS`:

```text
capture_date, timestamp_parsed, Dst Port, Flow Duration,
Tot Fwd Pkts, Tot Bwd Pkts, TotLen Fwd Pkts, TotLen Bwd Pkts,
Flow IAT Mean, Flow IAT Std, SYN Flag Cnt, ACK Flag Cnt, RST Flag Cnt,
Pkt Len Mean, Pkt Len Std
```

`Label`, `binary_attack_state`, `future_attack_state`, and
`future_target_available` are not required and are never generated. If a
label is present in a caller's frame, inference mode still does not use it.

## Output

The result contains exactly these columns, in this order:

```text
flow_count, byte_sum, packet_sum, mean_duration, median_duration,
mean_iat, iat_std, syn_flow_ratio, ack_flow_ratio, rst_flow_ratio,
fwd_byte_share, fwd_packet_share, unique_destination_port_count,
bytes_per_second, packets_per_second, packet_size_mean, packet_size_std,
timestamp, capture_day
```

`src.streaming.state_aggregator.aggregate_flow_window` returns the same
inference state contract for one completed 10-second flow window.

## Guarantees

- The feature formulas are shared with the supervised aggregator; there is no
  second feature schema.
- Features are numeric and finite; NaN and Inf are rejected.
- Timestamps are floored to the existing 10-second half-open intervals.
- Empty intervals between observed intervals are retained as zero-feature
  states by the shared aggregator.
- Aggregation never crosses a `capture_day` boundary.
- No label, binary state, future target, or fabricated target is emitted.

## Model boundary

This contract supplies model inputs only. It does not itself authorize a
forecast, an attack claim, a calibrated probability, or any change to the
frozen target, threshold, model weights, or operating policy.
