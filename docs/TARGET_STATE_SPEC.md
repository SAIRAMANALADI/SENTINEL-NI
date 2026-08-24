# Future Target State Specification

Schema version: `network-state-v1.0`

## Target name and type

`future_attack_state`: binary state-level target (`int8`).

## Source-label rule

For each valid flow, define:

```text
malicious_flow = 1 if Label != "Benign"
                 0 if Label == "Benign"
```

This preserves the original source labels in the flow artifact and treats every observed non-Benign source label as malicious traffic for this aggregate target. It does not map labels to MITRE ATT&CK and does not claim that one flow means the network is compromised.

## State metadata

For each 10-second state, compute:

```text
malicious_flow_count = sum(malicious_flow in the current state)
malicious_flow_ratio = malicious_flow_count / flow_count, or 0 for an empty state
binary_attack_state = 1 if malicious_flow_count > 0 else 0
```

These are target/ground-truth metadata, not model-input features.

## Future target

For a state at timestamp `t`, the one-step target is:

```text
future_attack_state(t) = binary_attack_state(t + 10 seconds)
```

The target is created by shifting state labels one row forward within the same `capture_day` after fixed interval construction. It never uses the next capture day. The last state of each day has no future interval and is encoded as `future_attack_state=-1` with `future_target_available=false`; it must be excluded from supervised target rows by the modeling layer.

For K-step forecasting, the same rule extends to `binary_attack_state(t + K * 10 seconds)` with all intermediate states remaining within the same capture day.

## Threshold investigation

Using the valid flow rows and all fixed states, the observed state-level frequency for the candidate count thresholds was:

| Interval | States | Empty states | `count >= 1` | `count >= 2` | `count >= 5` | `count >= 10` |
|---:|---:|---:|---:|---:|---:|---:|
| 1 second | 161,256 | 37.97% | 13.03% | 12.02% | 10.03% | 8.88% |
| 5 seconds | 32,252 | 35.33% | 14.18% | 13.85% | 13.25% | 12.33% |
| 10 seconds | 16,127 | 34.35% | 14.68% | 14.37% | 13.56% | 13.29% |
| 30 seconds | 5,376 | 32.50% | 16.56% | 16.35% | 14.21% | 14.17% |
| 60 seconds | 2,689 | 31.87% | 18.56% | 18.45% | 14.43% | 14.24% |

The MVP uses `count >= 1` because it is the least arbitrary rule that preserves detection of any observed malicious traffic, while the target name and documentation explicitly avoid interpreting that traffic as compromise. Higher thresholds are sensitivity experiments, not silently substituted labels.

## Edge cases and limitations

- Empty states have zero flow and malicious counts and therefore `binary_attack_state=0`.
- Terminal states have no future target and are marked unavailable with `-1` sentinel metadata.
- The 14 timestamp anomalies are excluded from temporal state construction and remain preserved in the raw/clean flow artifact.
- Source labels are schedule/IP/port/protocol-derived dataset labels; this target is not proof of attack stage, causal onset, or compromise.
- Completed flow aggregates may contain information from the full flow duration; an intra-flow early-warning interpretation would require a packet/time cutoff policy.
- The state table is flow-derived. Packet-only fields remain unavailable without PCAP.
