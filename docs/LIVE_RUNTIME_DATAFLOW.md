# Live Runtime Dataflow

## Single runtime path

```text
LiveTelemetryAdapter
    -> Runtime._on_live_event
    -> LiveRuntimeStore
       -> FlowBuilder
       -> SourceActivityAccumulator
       -> build_network_state_for_inference
       -> StateBuffer (L=10)
       -> predict_network_state_sequence (existing frozen path)
       -> source prioritization + recommendation-only mitigation
    -> GET /api/v1/live
    -> Authenticated Next.js dashboard
       (legacy Streamlit fallback is loopback/private)
```

## Ownership

- `src/telemetry/live.py` captures packet metadata and does not retain raw
  packet objects or payload bytes.
- `src/api/live_runtime.py` is the single bounded in-memory runtime store. It
  owns the live `FlowBuilder`, source activity windows, latest network states,
  the existing `StateBuffer`, latest forecast, source priorities, and
  recommendation-only mitigation output.
- `src/features/network_state.py` remains the shared feature implementation;
  the live path calls its existing label-free inference entry point.
- `src/forecasting/inference.py` remains the only model invocation path.
- `src/api/app.py` exposes the read-only `/api/v1/live` snapshot and retains
  the existing start/stop telemetry controls.
- `frontend/` reads the authenticated API, including `/api/v1/live`; it does
  not load the model, build states, or recompute forecasts.
- `app/streamlit_app.py` is a retained loopback/private demo fallback. It also
  reads `/api/v1/live` and does not load the model, build states, or recompute
  forecasts.

## State and restart behavior

Each successful live start begins a new bounded state session. The active
buffer, flow history, and state count reset so histories cannot cross live
capture sessions. The previous forecast is retained only as an explicitly
stale `last_forecast` record until a new live forecast replaces it.

Stopping capture does not delete the current forecast. The API marks it
`STALE_NOT_LIVE`, and the dashboard displays the stale status. No forecast is
created until ten valid states exist in the current session.

## Memory boundary

The store retains at most 4,096 completed flows, 128 state records, and 64
source-activity frames. Packet payloads are never retained. The API exposes
only the latest operational snapshot.
