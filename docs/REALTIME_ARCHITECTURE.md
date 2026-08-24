# Replay / Real-Time Architecture

The implemented integration path is offline deterministic replay. It feeds the frozen network-state contract into the existing inference API. Live packet capture is intentionally not implemented in this phase.

```text
approved replay source
  -> ReplayEvent source
  -> 10-second state aggregator
  -> strict StateBuffer (L=10)
  -> existing predict_network_state_sequence()
  -> existing operating policy and explanation
  -> CLI or Streamlit consumer
```

## Components

| Component | Current implementation | Contract |
|---|---|---|
| Replay source | `src/streaming/replay.py` | Emits source timestamps unchanged and in chronological order. Equal timestamps are allowed for raw flows; state timestamps are unique. Supports approved state files and CSE-CIC-IDS2018 flow CSVs. |
| Live source | Not implemented | Future adapter only; must emit the same `ReplayEvent` shape. |
| Packet/event collector | Not implemented | No packet capture or PCAP dependency is introduced. |
| 10-second aggregation buffer | `src/streaming/state_aggregator.py` | Delegates raw flow arithmetic to `aggregate_network_states()` and returns the same 17 feature names/units. |
| State validator | `validate_state()` and `StateBuffer` | Rejects NaN/Inf, wrong columns, wrong dates, duplicate/order violations, and non-10-second gaps. |
| Inference trigger | `src/streaming/realtime_engine.py` | Runs only after exactly 10 valid same-day states are buffered; then runs once for every new valid state. |
| Result stream | `EngineUpdate` | Carries buffering/waiting status or the existing inference result plus state index and processing time. |
| Streamlit consumer | `app/streamlit_app.py` | Offers Demo Replay and Static Sample modes. |

## Frozen-contract guarantees

- State interval remains exactly 10 seconds.
- Model input remains exactly 17 numeric flow-derived features in the order defined by `configs/state_feature_schema.yaml`.
- History length remains exactly 10 states.
- Capture-day boundaries never form one sequence.
- Missing intervals are reported as waiting; no interpolation is performed.
- The existing inference API remains the only model, policy, and explanation path.
- No target, threshold, checkpoint weights, or scientific artifact is changed by replay.
