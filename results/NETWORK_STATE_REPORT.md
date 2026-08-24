# Network State Report

## Result

The fixed-interval network-state table was built from the real multi-day flow artifact. The selected MVP interval is **10 seconds**. No model was trained.

| Measure | Value |
|---|---:|
| Total network states | 16,127 |
| Feature count | 17 |
| Valid input flows | 3,758,782 |
| Empty-state percentage | 34.3461% |
| Mean flows/state | 233.0739 |
| Median flows/state | 94.0000 |
| Excluded timestamp anomalies | 14 |
| Model-input missing/non-finite cells | 0 |

## States by capture day

```text
{
  "2018-02-14": 4320,
  "2018-02-21": 3167,
  "2018-02-22": 4320,
  "2018-02-28": 4320
}
```

## Future target distribution

`future_attack_state` uses `-1` for the final interval of each capture day because no future interval exists. The final forecasting target is otherwise `1` when the next interval contains at least one non-Benign labeled flow, and `0` otherwise.

```text
{
  "-1": 4,
  "0": 13756,
  "1": 2367
}
```

## Feature quality

- All `17` model-input features are finite and non-missing.
- Labels are not included in the feature columns.
- State rows are chronologically ordered within each capture day.
- No aggregation crosses a capture-day boundary.
- Source IP and destination IP fan-out are unavailable in this flow artifact and were not fabricated.
- Packet TTL, fragments, retransmissions, packet-accurate IAT/order, and other PCAP-only fields remain unavailable.

## Comparison

See `results/TEMPORAL_GRANULARITY_COMPARISON.md` for all measured candidate intervals.
