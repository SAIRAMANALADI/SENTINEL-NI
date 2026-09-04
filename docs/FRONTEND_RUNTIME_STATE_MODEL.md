# Frontend Runtime State Model

## Purpose

The frontend displays the backend's runtime truth. A forecast, source ranking, or recommendation is never presented as current when the processing service is unavailable, telemetry is stopped, or the result is stale.

## Explicit modes

| Mode | Meaning | Allowed data |
| --- | --- | --- |
| `DEMO` | Prepared demonstration traffic returned by `/api/v1/demo`. | Demo forecast, ranked candidate sources, and recommendations. Never live telemetry. |
| `REPLAY` | Configured replay/mock runtime returned by `/api/v1/live`. | Backend replay state only; no demo result is mixed into it. |
| `LIVE` | Capture adapter is configured for a real interface. | Current live telemetry, state history, and forecast when ready. |

The demo response is isolated in the UI. Its `history_length` is the only history value shown for the demo; it is not combined with the live runtime buffer.

## Runtime states

- `INITIALIZING`: the first runtime request is pending.
- `REPLAY`: the configured non-live runtime is idle or waiting for replay input.
- `LIVE`: live capture is running before enough history exists for a forecast.
- `BUILDING_HISTORY`: live capture is running and the state history is below the required sequence length.
- `FORECAST_READY`: a current forecast exists for a running live session or a completed demo.
- `STALE`: a prior live forecast is retained, but the session is no longer current.
- `STOPPED`: capture is stopped and no current forecast exists.
- `CAPTURE_UNAVAILABLE`: the live adapter cannot access the configured capture interface.
- `ERROR`: the runtime reported a processing or model error.
- `BACKEND_UNAVAILABLE`: `/api/v1/live` or a readiness request failed to
  reach the central service. The frontend clears current live/demo data and
  renders the outage state only.
- `BACKEND_DEGRADED`: the central service responded with a structured 503
  readiness body. The frontend preserves reachable live data and shows the
  central readiness reason instead of claiming a network outage.
- `MOCK`: the backend explicitly reports mock/static telemetry; it is not
  relabeled as replay or live capture.

## Transitions

```text
startup -> INITIALIZING -> REPLAY or STOPPED
startup -> BACKEND_UNAVAILABLE

LIVE start -> LIVE -> BUILDING_HISTORY -> FORECAST_READY
FORECAST_READY -> LIVE while the next state is being formed
LIVE/FORECAST_READY -> STALE when capture stops or telemetry becomes stale
STALE -> LIVE after a new session starts and new history is collected
any state -> BACKEND_UNAVAILABLE on a failed health/live request
BACKEND_UNAVAILABLE -> INITIALIZING after a successful retry

Run demo -> DEMO
DEMO -> DEMO until a new demo runs or the backend becomes unavailable
```

## Freshness and result rules

- `LIVE_RUNNING` with recent telemetry: `DATA FRESH`.
- `LIVE_RUNNING` outside the adapter freshness window: `DATA STALE`.
- stopped with a recorded event: `LAST LIVE UPDATE: <timestamp>`.
- stopped without a recorded event: `NOT CURRENT`.
- demo data: `NOT LIVE`, never `DATA FRESH`.
- backend unavailable: no score, source ranking, mitigation, or old result is shown as current.

## History contract

`Forecast history x / 10` is the authoritative sequence buffer used by the live model. `Network states` is a separate total count. The demo uses its own reported history length. The UI does not label total state count as the forecast buffer.

## Restart semantics

Starting a new live session resets active event, flow, state, source, and mitigation counters. The prior forecast may be returned as `last_forecast` with `STALE_NOT_LIVE`, but it is never returned as the current forecast. A new session must build a fresh `x / 10` history.

## Operator wording

`Predictive warning` means the Forecast Score meets the configured operating threshold. It is an operating signal, not confirmation of an attack. Candidate sources are ranked evidence for review, not confirmed attribution. Mitigation is recommendation-only; automatic blocking is disabled and `Simulation only: TRUE` remains visible.
