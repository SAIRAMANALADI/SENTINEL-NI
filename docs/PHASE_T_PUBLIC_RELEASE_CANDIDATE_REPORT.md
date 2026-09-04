# Phase T — Public Release Candidate Report

Validation date: 2026-09-04  
Repository: `SIH26` / `sih26-26153`  
Python package: `0.1.0`  
Agent CLI: `0.2.0`

## Decision

**OPEN-SOURCE RELEASE READY**

This classification means the documented local/open-source workflow is
coherent, the frozen runtime contract is preserved, and the available
validation gates pass. It does **not** mean `STAGING READY`, production
capacity, high availability, public ingress, or universal platform support.

The release remains deliberately out of band: customer requests go directly to
the customer's application. Sentinel observes traffic in parallel through a
local or remote sensor; it does not proxy, delay, block, or automatically
change customer traffic.

## 1. Scope and freeze boundary

Phase T made release/documentation hardening changes only. No new ML method,
feature, dataset, label, target rule, preprocessing rule, forecast horizon,
or runtime model artifact was introduced.

One small frontend journey fix was included: Add Sensor no longer pre-fills the
dashboard origin as the agent's central endpoint. It now starts empty, uses an
HTTPS reverse-proxy placeholder, and explains that the browser does not
register agents or handle credentials.

The protected contract remains:

| Contract | Verified value |
| --- | --- |
| State cadence | 10 seconds |
| Model context | `L=10` states |
| Forecast output | `K=5`, direct `+10s` through `+50s` |
| Input schema | 17 numeric flow-derived features in the approved order |
| Operating threshold | `0.19` |
| Terminology | Forecast Score / Predictive Warning / No Predictive Warning |
| Response boundary | Recommendation and simulation only |

The working tree contains pre-existing implementation changes from Phases
Q/S. The Phase T edits did not touch protected ML/data paths; the release audit
and full regression suite passed against the resulting tree.

## 2. Architecture and first-time user journey

The README and operator documentation now show one unambiguous primary path:

```text
Overview
  -> Sensors
  -> Add Sensor
  -> Sensor Detail
  -> Forecast
  -> Sources
  -> Mitigation
```

The real sensor lifecycle is:

```text
Central admin issues one-time enrollment credential
  -> agent wheel installed on monitored server
  -> init and register on that server
  -> config validate and start
  -> fresh heartbeat + accepted 10-second telemetry
  -> sensor ONLINE / FRESH
  -> valid L=10 history
  -> existing K=5 forecast
```

The browser never receives the runtime credential and never asks Central to
capture a remote interface. Replay/Demo is secondary, uses prepared data, and
is labeled as non-live. Forecast output is withheld when a sensor is offline,
stale, errored, or below the valid contiguous history requirement.

## 3. Evidence matrix

| Gate | Result | Evidence |
| --- | --- | --- |
| README/docs architecture and customer-path boundary | **PASS** | README operating model, first-time path, operator quickstart, deployment runbook |
| Primary dashboard journey | **PASS** | Browser smoke visited Overview, Sensors, Add Sensor, Forecast, Sources, Mitigation, and System |
| Sensor onboarding clarity | **PASS** | Add Sensor showed admin credential, install, register, start, heartbeat, telemetry, and online stages |
| Offline/stale/error behavior | **PASS** | Current browser showed selected sensor `OFFLINE`, `STALE TELEMETRY`, actionable retry/backend state; Forecast showed no output |
| Real vs demo separation | **PASS** | Replay showed `DEMO MODE`, prepared traffic, and “not live network telemetry”; Phase S showed real sensor mode |
| Forecast readiness guard | **PASS** | Current offline sensor showed `Forecast not ready yet`; Phase S reached `10/10` and emitted five rows only after readiness |
| Source attribution boundary | **PASS** | UI says candidate sources are ranked evidence, not confirmed attribution; remote state-only path does not claim attribution |
| Mitigation safety | **PASS** | UI says Simulation only / Automatic blocking disabled / recommendation only |
| API contract and security tests | **PASS** | `py -m pytest -q`: 319 passed, 2 warnings |
| Agent CLI surface | **PASS** | `--help` for root, init, register, start, stop, restart, status, config, diagnostics, and service; version smoke passed |
| Clean wheel installation | **PASS** | Fresh temporary venv installed the non-editable wheel; package metadata and `sentinel-agent --help/--version` worked |
| Package content audit | **PASS** | Wheel: 95 files; sdist: 185 files; no credentials, `.env`, result/cache, checkpoint, or dataset artifacts; expected Python `src/models` modules are source code, not model weights |
| Frontend typecheck/build | **PASS** | `npm run typecheck`; `npm run build` |
| Compose configuration/runtime | **PASS** | `docker compose config -q`, restart, down/up, all three services healthy, backend health/readiness 200 |
| Registry persistence | **PASS** | Six registered sensor identities remained after Compose down/up; process-local runtime history reset as documented |
| HTTPS and TLS verification | **PASS (inherited local evidence)** | Phase P/S isolated Nginx HTTPS path, trusted private CA, wrong CA and hostname mismatch rejection; expired/public certificate not verified |
| Real remote forecast path | **PASS (Phase S)** | Wi-Fi/Npcap agent reached contiguous `L=10`, existing LSTM returned five rows, rolling update observed, dashboard showed `ONLINE/FRESH/FORECAST READY/10/10` |
| Windows agent stop | **PASS (Phase S)** | Actual foreground process stopped with `sentinel-agent stop`; no matching process or PID/request file remained |
| Customer-path isolation | **PASS** | Independent local customer HTTP service returned 200 while Sentinel backend was stopped; Sentinel endpoint was unreachable during the stop |
| Release audit | **PASS after report creation** | `scripts/release_audit.py` passed after the Phase T report links existed; ignored local artifacts were warnings only |
| TruffleHog | **NOT VERIFIED** | `trufflehog` executable is not installed in this environment |
| Physical multi-host / five sensors | **NOT VERIFIED** | No second physical host was available |
| 30-minute soak / resource series | **NOT VERIFIED** | No sustained CPU/RAM/queue/capacity series was collected |
| Expired certificate / public ingress | **NOT VERIFIED** | Local private-CA and proxy evidence is not public staging evidence |

## 4. Browser smoke details

The current frontend at `http://127.0.0.1:3000/` was inspected through the
operator path. The current selected sensor was intentionally offline after the
Phase S process cleanup, so the browser showed the honest stale/offline state:

- Overview: fleet counts, real sensor status, no fabricated forecast.
- Sensors: six registered identities, separate Agent/Telemetry/Forecast health,
  and `0/10` or `10/10` history shown per sensor.
- Add Sensor: real command lifecycle and credential boundary.
- Forecast: no rows while the selected sensor was offline; readiness copy was
  visible.
- Sources: no source data and explicit non-attribution wording.
- Mitigation: simulation-only banner and no automatic blocking.
- Replay: prepared demo produced five labeled forecast horizons and
  recommendation/source sections without calling it live telemetry.
- System: replay/runtime status and “No payloads retained in the frontend.”

The earlier Phase S live dashboard observation is retained in
[`PHASE_S_REMOTE_FORECAST_AND_AGENT_STOP_REPORT.md`](PHASE_S_REMOTE_FORECAST_AND_AGENT_STOP_REPORT.md).

## 5. Security and privacy review

- Production HTTPS enforcement and trusted-proxy handling are covered by the
  API security tests and the Phase O/P/S local TLS evidence.
- Production agents retain certificate verification; no `curl -k` or
  `verify=False` path was used for the validated run.
- Enrollment credentials are short-lived and one-time; runtime credentials are
  sensor-specific, stored protected locally, and hashed centrally.
- State payloads are bounded and authenticated. Raw packet payloads are not
  forwarded by the remote path.
- Rate limits, sequence checks, duplicate protection, feature validation,
  capture-day checks, and bounded buffers remain enforced.
- Candidate sources are evidence rankings, not attacker identity. Mitigation
  does not mutate firewall or application policy.
- TruffleHog remains **NOT VERIFIED** because it was not installed. The release
  audit is a separate tracked-file hygiene and obvious-secret-pattern check.

## 6. Phase progression and stale-claim cleanup

Phase Q and Phase R reports remain historical records of runs that ended below
`L=10`. Phase S superseded those runtime findings by proving the real
forecast-ready path and Windows stop behavior. The current README, release
notes, environment matrix, checklist, and deployment runbook now point to the
current evidence while retaining historical reports unchanged.

The release documentation intentionally continues to mark these as unverified:
physical multi-host/five-sensor operation, long soak/resource capacity,
expired-certificate behavior, public DNS/ingress, Linux physical service
operation, TruffleHog, HA, OIDC, mTLS, tenant isolation, and automatic response.

## 7. Reproduction commands

```text
py -m pytest -q
Set-Location frontend; npm run typecheck; npm run build
py -m build
py scripts/release_audit.py
docker compose config -q
docker compose restart
docker compose down
docker compose up -d
```

The final local Compose stack was restored after the outage and down/up checks.
The remote agent was left stopped; no customer traffic is routed through the
stack.

## Final release statement

Phase T closes the public release-candidate documentation and validation pass
for the evidence available on this host. Ship as an open-source release
candidate with the environment matrix and limitations attached. Do not label
this artifact staging-ready or production-ready until the remaining physical,
public-ingress, certificate-expiry, soak, and secret-scanner gates are run in
their intended environments.
