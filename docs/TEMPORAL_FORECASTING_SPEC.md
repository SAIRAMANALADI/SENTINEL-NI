# Temporal Forecasting Specification

## Status

Implemented V1 offline forecasting contract. The LSTM checkpoints are development models; no final architecture winner or calibrated probability claim is made.

## State and input

Each state is a whole-network flow-derived summary at a fixed 10-second interval. The active model consumes the last 10 states and exactly 17 numeric features in the order defined by `configs/state_feature_schema.yaml`.

```text
[S(t-90s), S(t-80s), ..., S(t)] -> future state scores
```

The window builder rejects missing, duplicate, non-monotonic, cross-date, and non-10-second timestamps. Windows are isolated by capture day and split.

## Target

```text
binary_attack_state(t) = 1 if the current state contains at least one non-Benign source flow
future_attack_state(t) = binary_attack_state(t + 10 seconds)
```

Terminal states without a future interval are unavailable and excluded from supervised windows. For K-step direct forecasting, the target vector is the next K current-state labels at +10s increments within the same capture day. K=1 is verified against the approved `future_attack_state` column.

## Implemented output contract

```json
{
  "model_version": "LSTM-DEVELOPMENT-V1-direct-multistep-K5",
  "reference_timestamp": "2018-02-22T01:01:30",
  "forecast_horizon_seconds": 50,
  "forecast": [
    {"step": 1, "horizon_seconds": 10, "timestamp": "...", "score": 0.0, "warning": false},
    {"step": 2, "horizon_seconds": 20, "timestamp": "...", "score": 0.0, "warning": false},
    {"step": 3, "horizon_seconds": 30, "timestamp": "...", "score": 0.0, "warning": false},
    {"step": 4, "horizon_seconds": 40, "timestamp": "...", "score": 0.0, "warning": false},
    {"step": 5, "horizon_seconds": 50, "timestamp": "...", "score": 0.0, "warning": false}
  ],
  "operating_mode": "balanced",
  "threshold": 0.19
}
```

`score` is the raw model output after sigmoid and is displayed as **Forecast Score**. It is not a calibrated probability, confidence, risk percentage, or uncertainty estimate. The thresholded state is **Predictive warning** or **No predictive warning**, not attack confirmation.

## Checkpoints

| K | Checkpoint | Horizon | Output |
|---:|---|---:|---|
| 1 | `models/lstm_multistep_k1.pt` | +10s | one score |
| 3 | `models/lstm_multistep_k3.pt` | +10s, +20s, +30s | three scores |
| 5 | `models/lstm_multistep_k5.pt` | +10s through +50s | five scores |

The primary demo uses K=5. Checkpoint selection and threshold selection use validation only; the 28-Feb test day remains held out for final evaluation.

## Limitations

The four-day dataset does not prove broad temporal generalization. Flow-derived completed-flow statistics do not establish packet-cutoff early warning. Packet-level enrichment, calibrated probabilities, causal explanations, and attack-stage attribution are outside this V1 contract.
