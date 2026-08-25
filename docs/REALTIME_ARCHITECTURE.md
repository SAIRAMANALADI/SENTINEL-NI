# Replay / Real-Time Architecture

The implemented integration path supports offline deterministic replay and an
explicit, host-level live packet metadata adapter. Live capture is optional and
does not replace the approved offline network-state contract.

```text
approved replay source
  -> ReplayEvent source
  -> 10-second state aggregator
  -> strict StateBuffer (L=10)
  -> existing predict_network_state_sequence()
  -> existing operating policy and explanation
  -> CLI or Streamlit consumer

explicit live interface + Scapy/Npcap/libpcap
  -> LiveTelemetryAdapter (metadata only)
  -> existing SourceActivityAccumulator
  -> source prioritization / mitigation recommendation

Raw live packet metadata does not contain the flow fields required by the
frozen 17-feature network-state aggregator. Therefore live source activity is
not presented as live model inference until an approved packet-to-state
contract exists.
```

## Components

| Component | Current implementation | Contract |
|---|---|---|
| Replay source | `src/streaming/replay.py` | Emits source timestamps unchanged and in chronological order. Equal timestamps are allowed for raw flows; state timestamps are unique. Supports approved state files and CSE-CIC-IDS2018 flow CSVs. |
| Live source | `src/telemetry/live.py` | Explicit interface, Scapy backend, same packet-event fields, bounded metadata queue. |
| Packet/event collector | `LiveTelemetryAdapter` | Host-level only unless a separately secured capture-capable container is configured. |
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
