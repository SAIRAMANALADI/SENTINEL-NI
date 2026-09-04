# Phase S Remote Forecast and Agent Stop Report

Validation date: 2026-09-04  
Repository: SIH26  
Final classification: **OPEN-SOURCE RELEASE READY**

## Scope and freeze

Phase S closed two concrete issues:

1. prove the real remote path from Wi-Fi/Npcap capture through `L=10`, the
   existing LSTM `K=5` inference, and the operator dashboard;
2. replace the Windows `sentinel-agent stop` failure that returned
   `[WinError 87]`.

The protected ML/data contract was not changed: the existing LSTM weights,
architecture, inference function, scaler/preprocessor, 17 feature columns,
target semantics, `L=10`, `K=5`, threshold `0.19`, and training/evaluation
pipeline remain unchanged. No state, history item, forecast, score, or success
flag was injected. The live collector fix only chooses a non-retroactive state
window watermark from packet capture timestamps; it does not use wall-clock
receive time or alter measured flow fields.

## Root causes and fixes

### Remote state path

The first live run exposed two real ordering problems:

- the collector emitted only non-empty completed-flow windows, so sparse traffic
  could not form the canonical 10-second sequence;
- a flow that completed later was initially assigned to its first-packet
  timestamp. Idle/active timeout closures could therefore reopen an already
  emitted historical window and correctly receive a central `422` rejection.

`AgentCollector` now uses the existing inference-safe state aggregator to fill
  missing 10-second intervals with the canonical zero state. Completed flows
  are scheduled using the current packet's capture timestamp as the completion
  watermark, while first/last packet timestamps and all measured feature values
  remain present. Shutdown flush also skips states at or before the last emitted
  state, preventing duplicate retroactive delivery.

When a central gap resets a sensor's strict history, `RemoteSensorRuntime` now
clears the prior forecast. This keeps the dashboard contract truthful:
history below 10 is `FORECAST WAITING`, not a stale `FORECAST READY` result.

### Windows stop

The prior implementation called `os.kill(pid, SIGTERM)` on Windows, which
returned `WinError 87` and was unsafe around stale or reused PIDs. The fixed
implementation uses an agent-specific sibling stop-request file, verifies
Windows process liveness through the Windows process API, waits a bounded 10
seconds for the foreground agent's own graceful shutdown, and removes stale
control files. It never terminates an unrelated process by PID.

## Real end-to-end evidence

The final real run used a fresh registered remote identity with the actual
foreground `sentinel-agent`, Wi-Fi/Npcap capture, real outbound HTTPS traffic,
the rebuilt Compose backend, and the existing inference artifacts.

Sensor: `sensor-388dea7af4a84c71`  
Agent: `0.2.0`, interface `Wi-Fi`  
Central: local Docker Compose development API; HTTPS proxy behavior was already
validated in the Phase Q/O evidence and was not reclassified by this local
development run.

The monitor harness remained read-only and polled sensor detail only. At the
first real readiness observation it reported:

| Field | Observed result |
| --- | --- |
| Agent / telemetry | `ONLINE` / `FRESH` |
| Accepted state history | `10 / 10` |
| State count | `10` |
| Latest state | `2026-09-04T10:12:20+00:00` |
| Forecast status | `FORECAST_READY` |
| Forecast updates | `1` |
| Forecast row count | `5` |
| Forecast timestamps | `10:12:30`, `10:12:40`, `10:12:50`, `10:13:00`, `10:13:10` UTC |
| Forecast scores | `0.020820`, `0.021368`, `0.022315`, `0.024346`, `0.028546` |
| Warning rows | five `false` values |

The real rolling window then advanced to `state_count=11` and
`forecast_update_count=2`; its five forecast timestamps advanced by one
10-second horizon. A later rebuilt-backend run again reached `history_length=10`
and returned five forecast rows.

The rebuilt live run recorded two strict `422` responses during its shutdown
flush, after the forecast had already been proven; these were retroactive
duplicate flush states, not accepted bad data or a forecast-path failure. The
final no-reemit guard was added immediately afterward and is covered by the
focused duplicate-free flush regression; no claim is made that this last guard
was separately exercised in another long live run.

## Dashboard evidence

The actual operator dashboard at `http://127.0.0.1:3000` was opened to the
selected sensor detail. It visibly showed:

- `SENSOR ONLINE` and `Telemetry FRESH`;
- `Forecast READY` and `10 / 10 states`;
- `Capture RUNNING` and `CONNECTED`;
- five forecast points at `+10s`, `+20s`, `+30s`, `+40s`, and `+50s`;
- operating threshold `0.19` and rendered forecast scores.

This is the real sensor view, not Replay/Demo mode. The dashboard's forecast
state was derived from the central sensor and forecast endpoints.

## Stop, restart, and identity evidence

- `py -m src.agent stop` returned `stopped` for the actual foreground process.
- The agent logged `shutdown_requested` followed by `agent_stopped`.
- A fresh start of the same configuration retained
  `sensor-388dea7af4a84c71`; central accepted the resumed heartbeat and later
  telemetry sequences.
- Final cleanup found no `agent.pid`, no `.pid.stop` request file, and zero
  matching `src.agent start` processes.

The strict runtime reset behavior after a timestamp gap is now covered so a
previous forecast cannot remain visible while the new history is below 10.

## Tests and verification

Focused Phase S validation passed:

```text
py -m pytest -q tests/test_agent_stop.py tests/test_sensor_agent.py tests/test_live_inference_state.py tests/test_sensor_runtime.py
31 passed
```

The focused tests cover real subprocess graceful stop, missing/stale PID
idempotence, wrong-PID non-termination, canonical empty intervals, late flow
completion, idle completion, duplicate-free flush, and forecast clearing after
strict history reset.

Final verification completed:

- `py -m pytest -q`: **319 passed, 2 warnings**;
- `npm run typecheck`: passed;
- `npm run build`: passed;
- `py -m build`: wheel and sdist built;
- `py -m pip check`: no broken requirements;
- `py scripts/check_environment.py`: `PASS`;
- `py scripts/release_audit.py`: `RELEASE_AUDIT=PASS`;
- `docker compose config -q`: passed;
- `docker compose ps`: backend, dashboard, and frontend healthy;
- `git diff --check`: passed with only existing LF/CRLF normalization warnings;
- protected ML/data diff query: no changed protected artifact/schema paths.

## Limitations and decision

This proves the real remote sensor path and Windows stop behavior on the
available Windows host. It does not prove a physical multi-host or five-sensor
deployment, a 30-minute resource soak, expired public certificate behavior,
public ingress, or production capacity. The local Compose run therefore does
not justify changing the release classification to `STAGING READY`.

Phase S result: **REMOTE L=10 FORECAST PASS** and **WINDOWS AGENT STOP PASS**.  
Overall release classification remains: **OPEN-SOURCE RELEASE READY**.
