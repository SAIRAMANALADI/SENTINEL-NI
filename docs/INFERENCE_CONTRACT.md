# Offline Inference Contract

## Input

The stable API accepts one `pandas.DataFrame` containing exactly 10 chronological network states. The columns must appear in this order:

1. the 17 features from `configs/state_feature_schema.yaml`;
2. `timestamp`;
3. `capture_day`.

The 17 feature order is:

`flow_count`, `byte_sum`, `packet_sum`, `mean_duration`, `median_duration`, `mean_iat`, `iat_std`, `syn_flow_ratio`, `ack_flow_ratio`, `rst_flow_ratio`, `fwd_byte_share`, `fwd_packet_share`, `unique_destination_port_count`, `bytes_per_second`, `packets_per_second`, `packet_size_mean`, `packet_size_std`.

All feature columns must be numeric and finite. Timestamps must be valid, strictly ordered at 10-second intervals, and belong to one `capture_day`. The API rejects missing/extra columns, wrong order, wrong length, NaN, Inf, invalid timestamps, and mixed capture days.

The CLI accepts `.csv`, `.tsv`, and `.parquet` files with the same columns.

## Processing

- Feature schema: `configs/state_feature_schema.yaml`, schema version `network-state-v1.0`.
- Preprocessing artifact: `models/baseline_preprocessor.joblib`, fitted on the approved training states only.
- Model checkpoint: `models/lstm_multistep_k5.pt`.
- Model: direct multi-output LSTM, K=5, CPU inference.
- Forecast interval: 10 seconds; outputs cover +10s, +20s, +30s, +40s, and +50s.
- Operating policy: `configs/operating_policy.yaml`.
- Primary mode: `balanced`; its threshold is loaded from the policy file and is not hard-coded in the inference module.

The model uses the transformed 10-by-17 sequence. The policy threshold is applied to each direct K=5 score for the structured result; the primary demo interpretation is the +10-second output.

## Output

`predict_network_state_sequence(sequence)` returns one JSON-serializable mapping containing model/schema/target versions, the reference timestamp, five forecast rows, operating mode, threshold, explanation, and measured timing fields.

Each forecast row contains:

- `step`
- `horizon_seconds`
- `timestamp`
- `score` — raw model output called **Forecast Score**
- `warning` — boolean policy result

The explanation contains top feature-position contributions, aggregate temporal positions, method, and an explicit `causal_claim: false`. Sensitivity is described as model-score response; it is not causal attribution.

## Terminology

- **Forecast Score:** raw LSTM output, not a calibrated probability.
- **Predictive warning:** score is greater than or equal to the active policy threshold.
- **No predictive warning:** score is below the active policy threshold.

Never describe this output as “attack detected,” confirmed intrusion, confidence, or an attack technique.
