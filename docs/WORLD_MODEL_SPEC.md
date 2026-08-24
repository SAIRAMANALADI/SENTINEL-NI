# World Model Specification

## Status

This document describes the implemented frozen V1 temporal development model. It is an offline prototype contract, not a claim of final architecture selection or production readiness.

## Input

- Dataset: `data/processed/cic_ids2018_network_states.parquet`
- Split artifacts: `data/processed/states/train.parquet`, `validation.parquet`, `test.parquet`
- State interval: exactly 10 seconds
- Sequence length: 10 states
- Input tensor: `(batch, 10, 17)`
- Feature order: `configs/state_feature_schema.yaml`
- Features: the 17 flow-derived state features only; timestamps, capture-day metadata, labels, and targets are excluded.

## Target

The approved one-step target is:

```text
future_attack_state(t) = binary_attack_state(t + 10 seconds)
```

The future state remains within the same `capture_day`. For direct K-step experiments, the output vector at origin `t` is:

```text
[binary_attack_state(t+10s), ..., binary_attack_state(t+K*10s)]
```

K=1 is checked against the stored `future_attack_state` at the final input row. No target is shifted twice.

## Model

The implementation is a CPU-compatible one-layer LSTM encoder with a linear output head. The frozen development checkpoints are:

| Checkpoint | K | Horizon seconds | Output shape |
|---|---:|---:|---|
| `models/lstm_multistep_k1.pt` | 1 | 10 | `(batch, 1)` |
| `models/lstm_multistep_k3.pt` | 3 | 30 | `(batch, 3)` |
| `models/lstm_multistep_k5.pt` | 5 | 50 | `(batch, 5)` |

Each checkpoint/config records its K steps separately from its horizon seconds, feature schema, target definition, split days, seed, class weights, validation threshold-selection split, and checkpoint-selection metric.

## Score and policy

The model output is a raw **Forecast Score** in `[0,1]` after sigmoid. It is not a calibrated probability. The primary demo loads `configs/operating_policy.yaml`, uses Balanced mode, and applies the configured threshold independently to each direct forecast score. The UI labels results **Predictive warning** or **No predictive warning** and does not claim attack detection or confirmation.

## Evaluation controls

- Train: 2018-02-14 and 2018-02-21
- Validation: 2018-02-22
- Test: 2018-02-28
- Positive-class weights: training windows only
- Checkpoint selection: mean validation PR-AUC across forecast steps
- Threshold selection: validation split only
- Final test: evaluated after selection; not used for tuning

## Limitations

- Four capture days and one final test day do not establish broad temporal or environment generalization.
- K=1/K=3/K=5 are controlled development experiments; no final architecture winner is claimed.
- State features are flow-derived completed-flow aggregates, not packet-cutoff observations.
- PCAP-only fields and defensible flow-to-PCAP matching are unavailable.
- Scores are not calibrated probabilities, and explanations are sensitivity responses, not causal attribution.
