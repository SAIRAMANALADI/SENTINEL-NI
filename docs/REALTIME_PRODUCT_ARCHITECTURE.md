# Sentinel / NI Real-Time Product Architecture

Sentinel / NI is a single-node, self-hostable network-state forecasting
service. Its production boundary is the traffic visible to one explicitly
configured telemetry source; it does not monitor the public internet by
itself.

```text
configured sensor interface / replay source
    -> packet-event adapter
    -> bounded bidirectional flow builder
    -> exact 10-second state aggregation
    -> bounded L=10 state history
    -> frozen K=5 forecast engine
    -> warning policy and source prioritization
    -> recommendation-only mitigation
    -> FastAPI current-state API
    -> Next.js operator interface
```

The backend owns one runtime per process. Browser sessions are readers of the
same current runtime state; opening another dashboard does not start another
sniffer or another model pipeline.

The scientific contract is frozen at 17 numeric state features, a 10-second
cadence, L=10 history, K=5 horizons, and the approved operating policy. The
forecast is a `Forecast Score`, not a calibrated probability. A ranked source
is a `Candidate Source`, not a confirmed attacker. Mitigation is always
simulation-only and never blocks traffic.

## Runtime boundaries

- `src/telemetry/` adapts packet or replay input to metadata events.
- `src/streaming/` owns flows, state aggregation, bounded history, and source
  activity.
- `src/forecasting/` invokes the frozen model and policy.
- `src/api/` owns lifecycle, readiness, authorization, and the authoritative
  current-state response.
- `frontend/` and `app/` render API state; they do not capture packets or run
  inference.

The live adapter retains metadata only. Payload contents are not stored by
default. Capture privileges should eventually be isolated in a dedicated
sensor process; the current implementation is host-level and single-node.
