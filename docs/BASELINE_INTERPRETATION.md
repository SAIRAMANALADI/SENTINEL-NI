# Logistic Regression Baseline Interpretation

## What the baseline does

The baseline consumes the 17 approved flow-derived features from one 10-second network state at time `t` and estimates the probability of the approved target:

```text
future_attack_state(t) = binary_attack_state(t + 10 seconds)
```

It provides a reproducible, auditable reference for precision, recall, F1, PR-AUC, ROC-AUC, false-positive rate, confusion matrix, and probability calibration. The decision threshold is selected using validation data only.

## What it does not do

- It does not consume temporal sequences, despite the source data being ordered by capture day.
- It does not model dependencies across multiple states.
- It does not forecast multiple future steps.
- It does not identify an attack chain, attack stage, compromise, or MITRE ATT&CK technique.
- It does not use raw labels, timestamps, capture-day identifiers, or target metadata as inputs.
- It does not provide packet-level evidence; the V1 state representation is flow-derived.

## Why this is not a temporal world model

The baseline maps one state vector to one future-state probability. It has no memory of earlier states and cannot represent temporal persistence, onset, burst evolution, or recovery across a sequence. The temporal window engine is validated separately, but no sequence model is trained in this baseline task.

## What a future LSTM/GRU must add

An LSTM/GRU should be judged against this baseline using the same day-aware partitions and approved target. It must add value through temporal context rather than through a changed target, a random split, or additional leakage. Any comparison must preserve the validation-only threshold-selection rule and report the held-out test result once.

## Current limitations

- The four capture days provide day-aware evaluation but limited scenario diversity.
- The target is observed malicious-traffic presence derived from source labels, not a causal compromise label.
- Completed flow aggregates may include information from the full flow duration, so this is not a packet-cutoff early-warning guarantee.
- TTL, fragmentation, retransmission, packet-order timing, payload distributions, complete TCP-window observations, and ordered TCP flags remain unavailable without a defensible matched PCAP.
- Class imbalance makes PR-AUC, recall, precision, F1, and false-positive rate more informative than accuracy; no single metric establishes deployment readiness.
