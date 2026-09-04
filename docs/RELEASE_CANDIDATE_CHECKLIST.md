# Release Candidate Checklist

Phase T validation date: 2026-09-04; superseded by Phase X on 2026-09-04
Legend: each item is marked **PASS**, **FAIL**, **NOT VERIFIED**, or **NOT APPLICABLE**; a passing local check is not a staging claim.

> **Current-status banner:** Phase X is the authoritative current validation
> overlay. The Phase Q/R/T items below are retained as historical evidence and
> must not be read as the final status when they conflict with Phase X.

## Core release checks

- [x] PASS — Package builds; wheel and sdist build passed.
- [x] PASS — Clean install and pip check passed.
- [x] PASS — `sentinel-agent --help` and version smoke passed.
- [x] PASS — Compose backend `/api/v1/health` and `/api/v1/ready` returned healthy/ready.
- [x] PASS — Actual agent registration through the TLS proxy succeeded.
- [x] PASS — Agent telemetry contract passed after the live-feature nesting fix; focused tests passed.
- [x] PASS — Actual HTTPS heartbeats reached central and status became ONLINE.
- [x] PASS — Sensor health transitions and stale telemetry behavior were observed.
- [ ] NOT VERIFIED — Multi-sensor physical deployment; no second physical host was available.
- [x] PASS — Isolated localhost TLS endpoint trusted by its private CA; wrong CA and hostname mismatch rejected.
- [x] PASS — Nginx reverse proxy forwarded HTTPS to the backend and overwrote `X-Forwarded-Proto`.
- [x] PASS — Docker Compose backend, dashboard, and frontend ran healthy with loopback-only host bindings.
- [x] PASS — Compose restart and down/up preserved registry identity via `./results/sensors`.
- [x] PASS — Automated outage/retry contracts passed.
- [ ] NOT VERIFIED — Physical outage recovery and active-agent reconnect after central outage.
- [x] PASS — Real Wi-Fi/Npcap capture emitted valid states with no collector drops.
- [x] PASS — Existing wrapper startup/release validation remained green; see [`PHASE_M_WRAPPER_FIX_REPORT.md`](PHASE_M_WRAPPER_FIX_REPORT.md).
- [ ] NOT VERIFIED — 30-minute soak; no long-run CPU/RAM/queue series was collected.
- [x] PASS — Frontend/dashboard primary journey smoke-tested; the Phase S run also showed the real sensor forecast-ready view.
- [x] PASS — Application security, HTTPS enforcement, package audit, and focused security tests passed.
- [ ] NOT VERIFIED — Expired certificate, five-sensor soak, and public production ingress.
- [x] PASS — Documentation, release audit, Compose config, and diff checks passed.
- [x] PASS — Model/data integrity check found no protected artifact diff.

## Phase Q final validation overlay

- [x] PASS — Real HTTPS agent registration and heartbeat through Nginx.
- [x] PASS — Real central outage buffering, retry, and post-restart flush observed.
- [x] PASS — Real agent stop caused OFFLINE/STALE state; same identity restarted.
- [x] PASS — Independent customer server remained HTTP 200 during Sentinel outage.
- [ ] NOT VERIFIED — Real L=10 context and existing K=5 forecast; live state history ended below 10.
- [ ] NOT VERIFIED — Dashboard showing the real sensor as forecast-ready.
- [ ] NOT VERIFIED — Physical multi-host/five-sensor run.
- [ ] NOT VERIFIED — Expired certificate behavior.
- [ ] NOT VERIFIED — 30-minute soak and resource time series.
- [ ] NOT VERIFIED — TruffleHog; it was not installed.
- [ ] NOT VERIFIED — Full live rate-limit/noisy-sensor and overflow exercise.

## Explicit release limitations

- The Docker run is a local Compose validation, not a multi-host staging deployment.
- TLS was validated only through an isolated localhost Nginx proxy and temporary private CA.
- Multi-host, five-sensor behavior, active outage recovery, and a 30-minute resource soak remain unverified.
- Phase S subsequently reached the required contiguous history and produced the
  existing five-row forecast. This current release-candidate evidence is
  consolidated in the Phase T report below.

Final classification: **OPEN-SOURCE RELEASE READY**.

This classification does not claim `STAGING READY` or production readiness; the
environment-validation limitations above remain explicit.

## Phase R remote forecast validation overlay

Validation date: 2026-09-04. This overlay records the real remote run; it does
not promote the release classification.

- [x] PASS — Real agent registration, HTTPS heartbeat, Wi-Fi/Npcap capture, and telemetry delivery exercised.
- [x] PASS — Central correctly rejected duplicate/gapped live state timestamps rather than fabricating a forecast.
- [x] PASS — Central outage buffering, retry backoff, and post-restart flush observed with the actual agent.
- [x] PASS — Agent stop produced OFFLINE/STALE state; same configuration restarted with the same sensor identity.
- [x] PASS — Independent customer HTTP service remained available during Sentinel backend interruption.
- [ ] NOT VERIFIED — Real contiguous `L=10` history and actual live `K=5` LSTM forecast.
- [ ] NOT VERIFIED — Live forecast scores/timestamps/warnings and forecast-ready dashboard state.
- [ ] NOT VERIFIED — Physical multi-host/five-sensor deployment.
- [ ] NOT VERIFIED — 30-minute soak, live resource/capacity series, expired certificate, TruffleHog, and live noisy-sensor/overflow exercise.
- [x] PASS — Full regression/package/frontend/Compose/release checks remained green after the validation-only harness/docs update.

The Phase R report is [`PHASE_R_REMOTE_FORECAST_REPORT.md`](PHASE_R_REMOTE_FORECAST_REPORT.md).
The final classification remains **OPEN-SOURCE RELEASE READY**; `STAGING READY`
is not claimed.

## Phase S remote forecast and Windows stop overlay

Validation date: 2026-09-04. This overlay records the completed real remote
forecast and Windows stop validation; it does not promote the release
classification.

- [x] PASS — Real Wi-Fi/Npcap agent path reached 10 contiguous accepted states with `history_length=10`.
- [x] PASS — Existing production LSTM inference returned exactly five forecast rows with unchanged threshold `0.19`.
- [x] PASS — Rolling window advanced and produced a second forecast update with five advanced horizons.
- [x] PASS — Actual operator dashboard showed the selected remote sensor as `ONLINE`, `FRESH`, `FORECAST READY`, and `10 / 10 states` with five visible forecast points.
- [x] PASS — Windows `sentinel-agent stop` gracefully stopped the actual foreground process and left no PID/request file or matching agent process.
- [x] PASS — Same configuration restarted with the same sensor identity and resumed authenticated heartbeat/telemetry.
- [x] PASS — Focused Phase S regression suite passed (`31 passed`).
- [ ] NOT VERIFIED — Physical multi-host/five-sensor deployment, 30-minute soak, expired certificate, public ingress, and live capacity/resource series.

The Phase S report is [`PHASE_S_REMOTE_FORECAST_AND_AGENT_STOP_REPORT.md`](PHASE_S_REMOTE_FORECAST_AND_AGENT_STOP_REPORT.md).
The final classification remains **OPEN-SOURCE RELEASE READY**; `STAGING READY`
is not claimed.

## Phase T public release-candidate overlay

Validation date: 2026-09-04. This is the current release gate after the Phase S
real forecast and Windows stop fix. Historical Phase Q/R entries above remain
historical records; this overlay is authoritative for the current candidate.

- [x] PASS — README, architecture, first-time operator path, and customer-path boundary are explicit.
- [x] PASS — Primary dashboard journey verified: Overview, Sensors, Add Sensor, Sensor Detail, Forecast, Sources, and Mitigation.
- [x] PASS — Secondary Replay/Demo journey is visibly labeled as prepared, non-live data.
- [x] PASS — Offline/stale/error states are actionable and forecast output is withheld until valid `L=10` history.
- [x] PASS — All documented agent CLI command groups exist and expose help without secrets.
- [x] PASS — Non-editable wheel installed in a fresh virtual environment; package contents contain no runtime credentials or local result/cache artifacts.
- [x] PASS — Current Python, frontend, package, Compose, security, and release-audit checks passed.
- [x] PASS — Local Compose restart and down/up lifecycle restored healthy services and preserved registered sensor identity.
- [x] PASS — Independent customer HTTP service remained available while Sentinel backend service was stopped.
- [x] PASS — Model/data freeze audit found no protected ML, feature, preprocessing, forecasting, or dataset edits.
- [ ] NOT VERIFIED — TruffleHog scan; executable was not installed in this environment.
- [ ] NOT VERIFIED — Second physical host, five-sensor run, 30-minute soak/resource series, expired certificate, and public ingress.

Current classification: **CONDITIONAL CANDIDATE — PUBLICATION PENDING PROVENANCE RECONCILIATION**.
Phase X is the current authority; this does not claim external validation or
production readiness.

The complete evidence is [`PHASE_T_PUBLIC_RELEASE_CANDIDATE_REPORT.md`](PHASE_T_PUBLIC_RELEASE_CANDIDATE_REPORT.md).
