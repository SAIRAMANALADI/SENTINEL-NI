# Phase R Remote Forecast Validation Report

Validation date: 2026-09-04  
Repository: SIH26  
Final classification: **OPEN-SOURCE RELEASE READY**

## Scope and guardrails

Phase R was a validation-only exercise. No ML artifact, feature definition,
forecast threshold, state cadence, telemetry schema, or data-pipeline behavior
was changed for this phase. The monitor harness added for repeatability is
read-only: [`scripts/phase_r_remote_forecast.py`](../scripts/phase_r_remote_forecast.py)
only polls an authenticated sensor-detail endpoint and emits JSON snapshots.

The protected ML/data paths were compared before and after the run and had no
Phase R changes. No state, score, history entry, or forecast was inserted
manually. No `verify=False`, `curl -k`, direct runtime injection, or fake
forecast was used.

## Environment actually exercised

- Docker Compose backend, dashboard, and frontend were healthy after cleanup.
- The actual installed `sentinel-agent` process ran on the monitored Windows
  host against the Wi-Fi interface using Scapy/Npcap.
- Central was reached through a temporary Nginx reverse proxy with a private CA
  and `tls_verify=true` in the agent.
- A fresh sensor registered through HTTPS and sent authenticated heartbeats and
  real telemetry.
- The live traffic stimulus was continuous outbound HTTPS traffic for about
  130 seconds. This is shorter than the requested 30-minute soak.

## Pipeline inspection

The unchanged production path is:

1. `AgentCollector` preserves packet timing and emits completed flow windows.
2. `FlowBuilder` closes flows on FIN/RST, idle timeout, active timeout, or
   flush.
3. The state aggregator emits the existing 10-second, 17-feature state.
4. `TelemetryBatcher` sends the nested `features` contract over the real
   telemetry API and retains unsent batches in the bounded buffer.
5. `RemoteSensorRuntime` owns sensor-scoped history with `L=10` and resets on
   invalid gaps.
6. The existing inference path requires `sequence_length=10`, `input_size=17`,
   and `output_size=5` before loading the LSTM/preprocessor/policy/schema.
7. When inference is possible, the existing forecast manager exposes five
   forecast rows and the dashboard renders forecast-ready state and warning
   semantics.

The API rejected duplicate or gapped 10-second timestamps, as required by the
existing contiguous-state contract. This protected the inference boundary but
prevented the live run from building a valid L=10 window.

## Evidence matrix

| Area | Result | Evidence and limit |
| --- | --- | --- |
| Agent registration | **PASS** | Fresh sensor registered through the real HTTPS proxy. |
| Authenticated heartbeat | **PASS** | Central observed the sensor online/fresh during the run. |
| Real capture | **PASS** | Wi-Fi/Npcap capture observed approximately 1,042 packets over a 22-second probe, with valid states and no collector drops. |
| Flow/state pipeline | **PASS partial** | Real packets reached flow building and state emission; duplicate/gapped state timestamps were rejected by contract. |
| 10-second cadence | **PASS contract / NOT VERIFIED end-to-end** | The implementation and API enforce the 10-second cadence; a contiguous live sequence was not completed. |
| L=10 history | **NOT VERIFIED** | Final fresh-sensor runtime was `state_count=7`, `history_length=1`, `history_required=10`. |
| LSTM inference | **NOT VERIFIED live** | No real remote forecast update was produced. Existing automated inference/contract coverage passed separately. |
| K=5 output | **NOT VERIFIED live** | No live five-row forecast payload or scores existed to inspect. The unchanged artifact contract requires five outputs. |
| Forecast timestamps/scores | **NOT VERIFIED live** | No forecast rows were available; no values were fabricated. |
| Dashboard forecast-ready state | **NOT VERIFIED live** | Dashboard/frontend health and build passed, but a real authenticated forecast-ready view was not reached. |
| Warning policy | **PASS contract / NOT VERIFIED live** | Existing threshold and warning semantics are covered by implementation/tests; no live forecast was available. |
| Central outage recovery | **PASS partial** | Actual agent buffered four batches, retried with 1/2-second backoff, and flushed after backend restart; zero-loss and production RTO are not claimed. |
| Agent outage/restart | **PASS partial / FAIL CLI stop** | Stopping the process produced central `OFFLINE`/`STALE`; restarting the same config preserved the sensor ID and restored heartbeat connectivity. The Windows `sentinel-agent stop` subcommand returned `[WinError 87]`, so Ctrl-C was used for cleanup. |
| Customer-path isolation | **PASS** | An independent customer HTTP server returned 200 before, during, and after Sentinel backend interruption. |
| Multi-sensor/physical multi-host | **NOT VERIFIED** | No second physical host or five-sensor run was available. |
| Invalid state/feature/cross-sensor rejection | **PASS automated / NOT VERIFIED live** | Existing negative API/security tests cover these boundaries; no live malformed injection was performed. |
| Rate limit/noisy sensor/overflow | **PASS automated / NOT VERIFIED live** | Automated bounds passed; no extended live noisy-sensor or overflow exercise was run. |
| Package/release checks | **PASS** | Package, clean install, `pip check`, frontend checks, Compose config, strict release audit, environment check, and diff check passed. |

## Required negative boundaries

The existing automated suite covers insufficient history, invalid state
timestamps, wrong feature count, sensor-scoped access, authentication,
rate-limit, and bounded-buffer behavior. Those tests passed in the full suite.
They are recorded as automated evidence only; they do not substitute for the
unavailable physical five-sensor and long-running live exercises.

## Exact result categories

### PASS

- Real HTTPS registration, heartbeat, capture, flow/state processing, and
  telemetry delivery were exercised.
- The central API preserved the contiguous-state boundary and rejected invalid
  duplicate/gapped live data rather than fabricating history.
- Central outage buffering/retry/flush, stale/offline transitions, same-identity
  restart, and independent customer traffic were observed.
- Existing regression, package, frontend, Compose, security, and release checks
  passed.

### FAIL

**FAIL — Windows stop command.** The `sentinel-agent stop` subcommand returned
`[WinError 87]` during cleanup; Ctrl-C stopped the foreground process. No
fail-open TLS, cross-sensor history contamination, unauthorized telemetry
acceptance, fabricated forecast, or customer-path dependency was observed.

### NOT VERIFIED

- A real contiguous `L=10` live window and actual `K=5` LSTM forecast.
- Live forecast scores, timestamps, warning rows, and forecast-ready dashboard.
- Physical multi-host/five-sensor operation, 30-minute soak, live capacity and
  resource series, expired-certificate behavior, TruffleHog scan, and live
  noisy-sensor/overflow exercise.

## Final decision

The requested real remote `L=10`/`K=5` forecast was **not proven** in this
environment. The correct release decision is therefore **OPEN-SOURCE RELEASE
READY**, retaining the explicit staging and production limitations. Phase R
stops here; no new feature or follow-on phase was created automatically.
