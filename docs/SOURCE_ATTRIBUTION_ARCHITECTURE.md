# Source Attribution Architecture

## Purpose

The source-attribution layer answers:

> Which observed sources are contributing to elevated activity in the current interval?

The existing forecasting layer continues to answer:

> Is the future network state becoming elevated?

These are separate questions and separate contracts. The source layer does not retrain, alter, or add inputs to the frozen LSTM.

## Runtime shape

```text
packet/event stream
        |
        v
packet-event validation
        |
        v
observed flow_5tuple + source_key
        |
        v
10-second source activity table
        |
        +--> candidate-source risk records
        |
        +--> transparent source prioritization
                    |
                    v
          recommendation-only mitigation

approved network-state replay
        |
        v
frozen 10-second network state
        |
        v
existing L=10, K=5 forecast API
        |
        +--> forecast context for source prioritization
```

## Implemented components

| Component | Implementation | Boundary |
|---|---|---|
| Packet event schema | `configs/packet_event_schema.yaml` | Validates supplied event fields; does not extract PCAPs. |
| Source aggregation | `src/streaming/source_activity.py` | Counts observed events by source and 10-second interval. |
| Candidate-source records | `src/evaluation/source_risk.py` | Preserves activity and labels records `candidate source`; no source probability. |
| Source prioritization | `src/streaming/source_forecast.py` | Transparent points from measured growth, rates, and diversity. |
| Mitigation policy | `src/evaluation/mitigation_policy.py` | Returns monitor/rate-limit/investigate recommendations only. |
| Rate simulation | `src/evaluation/rate_limit_simulator.py` | Offline deterministic arithmetic; no firewall changes. |
| Replay adapter | `src/streaming/replay.py` and `src/streaming/realtime_engine.py` | Optional packet events can emit source updates beside existing state replay. |
| Dashboard section | `app/streamlit_app.py` | Optional deterministic mock display, explicitly labeled prototype. |

## Frozen forecasting boundary

The default `RealtimeEngine` behavior is unchanged. Source events are enabled only with `source_activity_enabled=True`. Existing state replay still uses the exact 17-feature state contract, 10-second cadence, L=10 context, K=5 forecast, policy, and explanation paths.

The current source sidecar does not convert packet events into the frozen 17-feature network state. That conversion would require a separately approved packet/state contract and must not be inferred from the unverified CSE-CIC-IDS2018 PCAP archive.

## Data-status boundary

The deterministic mock stream demonstrates mechanics only. It is not CSE-CIC-IDS2018 evidence, not a production capture, and not a source-label validation set. The current CSE-CIC-IDS2018 flow artifact remains unsuitable for source fusion because it lacks source identity and canonical flow identifiers.
