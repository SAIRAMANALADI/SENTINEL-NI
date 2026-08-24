# Final System Architecture

The prototype is an offline forecasting system. Training and dataset construction are upstream activities; the repeatable demo consumes an approved 10-state network-state sequence through the frozen inference API.

| Stage | Input | Output | Purpose | Responsible module | Major limitation |
|---|---|---|---|---|---|
| Raw network traffic | CSE-CIC-IDS2018 source flow/traffic files | Source flow records | Provide the observed traffic source for offline dataset construction | Dataset artifacts and acquisition runbooks | V1 does not provide a live packet capture path; the 28-Feb PCAP matching path is blocked |
| Flow ingestion | CICFlowMeter CSV flow records | Validated canonical flow rows | Read chunks, normalize numeric fields, preserve labels, and reject malformed values | `src/ingestion/cic_ids2018.py` | Flow exports lack the identity fields needed for defensible packet matching |
| Feature engineering | Canonical flow rows and original labels | Flow-derived features and label metadata | Derive the approved numeric flow/state inputs without remapping labels to MITRE | `src/features/labels.py`, `src/features/network_state.py`, `src/features/timestamps.py` | Features are flow aggregates, not raw packet observations |
| 10-second network states | Valid flow rows grouped by `capture_day` and fixed timestamp intervals | `data/processed/cic_ids2018_network_states.parquet` | Preserve empty intervals, aggregate flow behavior, and keep complete capture-day boundaries | `src/features/network_state.py` | Completed-flow values can include information from a flow’s full duration |
| Future attack-state target | Current `binary_attack_state` by state | `future_attack_state(t) = binary_attack_state(t + 10s)` | Define a state-level future malicious-presence target within the same capture day | Target specification and state pipeline | It predicts observed attack-state presence, not compromise, intent, or technique |
| Temporal LSTM | 10 chronological states × 17 features | Hidden representation and direct logits | Learn a controlled temporal development model from approved sequences | `src/models/lstm_world_model.py` | Four capture days do not establish broad temporal generalization |
| K-step forecast | LSTM hidden state | K=1/K=3/K=5 future state scores | Produce direct +10s through +50s forecast outputs | `src/forecasting/multistep.py`, `src/forecasting/windowing.py` | The K=5 model remains a development/demo model, not a final architecture winner |
| Operating policy | Raw Forecast Scores and policy configuration | Warning/no-warning decisions | Apply validation-selected mode thresholds without retuning on final test | `src/evaluation/operating_policy.py`, `configs/operating_policy.yaml` | Scores are not calibrated probabilities; alert rates are state-rate estimates |
| Explainability | One standardized input sequence and frozen model | Feature-position and temporal sensitivity | Show which masked inputs changed the model score | `src/evaluation/feature_ablation.py`, `src/forecasting/explanation.py` | Sensitivity is not causal attribution |
| Offline inference API | Validated DataFrame with 10 states, 17 features, timestamps, and capture day | JSON-serializable forecast, policy, explanation, and timing result | Provide one stable service boundary for CLI and UI | `src/forecasting/inference.py` | Requires the approved local preprocessing artifact and K=5 checkpoint |
| Streamlit dashboard | Demo/uploaded compatible sequence | Human-readable forecast, trajectory, warning, explanation, and technical details | Present the real inference result for a judge/demo workflow | `app/streamlit_app.py` | It is an offline prototype, not a production live-monitoring service |

## Frozen contract

- State interval: 10 seconds.
- Model inputs: exactly 17 flow-derived numeric features.
- Primary demo forecast: K=5 checkpoint, first output at +10 seconds.
- Primary operating mode: Balanced.
- Balanced threshold: loaded from policy configuration, currently 0.19.
- UI terms: **Forecast Score**, **Predictive warning**, and **No predictive warning**.

The dashboard does not implement a second preprocessing, model, policy, or explanation path.
