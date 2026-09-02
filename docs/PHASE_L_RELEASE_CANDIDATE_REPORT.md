# Phase L Release Candidate Report

## Scope

This report records the final V0.1 release-candidate environment validation for Sentinel. The frozen data/network and ML contracts were not modified. No new model, feature, target, threshold, or dataset was introduced.

Overall classification: **OPEN-SOURCE RELEASE READY WITH ENVIRONMENT VALIDATION PENDING**.

This is the honest release classification from the Phase L decision set: the repository/package quality gates pass, while Docker runtime, real TLS, physical multi-host deployment, and browser validation against real sensors remain unverified.

## Frozen integrity boundary

The following remained unchanged during this phase:

- model/inference implementation and weights;
- 17 state features;
- target and forecast semantics;
- scaler;
- `L=10` sequence length;
- `K=5` forecast horizons;
- operating threshold `0.19`;
- source-attribution and mitigation semantics;
- local capture, replay, and mock telemetry contracts.

The protected-path diff was empty for the ML, forecasting, feature, ingestion, data, schema, target, and data-contract paths.

## 1. Environment

**PASS** for the available local Windows/Python/Npcap/Wi-Fi environment.
**NOT VERIFIED** for Docker Desktop runtime, Linux staging host, staging DNS/TLS, reverse proxy, or a second physical host.

Exact inventory: [`RELEASE_CANDIDATE_ENVIRONMENT.md`](RELEASE_CANDIDATE_ENVIRONMENT.md).

## 2. Topology

**PASS** for the intended out-of-band boundary in the code and documentation: Sentinel observes telemetry and does not sit in the customer application request path.
**NOT VERIFIED** for a real remote-server deployment because no second host or staging endpoint was available.

## 3. Docker runtime

**PASS** — `docker compose config --quiet` completed successfully.
**NOT VERIFIED** — `docker compose up`, container health/readiness, restart, down/up recovery, published-port inspection, and registry persistence could not be executed because the Docker daemon was unavailable.

Observed blocker:

```text
failed to connect to the Docker API at npipe:////./pipe/dockerDesktopLinuxEngine
The system cannot find the file specified.
```

Docker CLI and Compose being installed is not treated as Docker runtime validation.

## 4. TLS and reverse proxy

**NOT VERIFIED** — no staging hostname, certificate chain, or reverse proxy was available. The repository contains configuration/documentation but no live TLS handshake was performed. Port `8000` exposure through a real proxy was therefore not verified.

Certificate acceptance/rejection cases (valid CA, wrong CA, hostname mismatch, and expiry) are also **NOT VERIFIED** in a live TLS environment.

## 5. Remote agent

**PASS** — package build, clean wheel import/CLI smoke, CLI help, and automated agent/telemetry contract coverage passed. The package reports `sentinel-agent 0.2.0` and exposes the documented lifecycle commands.

**NOT VERIFIED** — physical installation, registration, heartbeat, and telemetry from a remote host to a central service over the intended deployment network.

## 6. Physical multi-host

**NOT VERIFIED** — no second physical host was available. Isolated local tests and automated tests are not being relabeled as physical multi-host evidence. Unique identity, independent forecasts, and cross-sensor isolation therefore remain staging work.

## 7. Real live capture

**PASS** — local real packet capture on host `RAMANA`, interface `Wi-Fi`, using the Npcap/libpcap-compatible path.

Evidence:

- 10-second smoke: `events_emitted=2962`, `status=LIVE_STOPPED`;
- independent direct API observation: `301.79` seconds;
- peak packets: `8068`;
- peak completed flows: `27`;
- peak valid states: `27`;
- peak forecast updates: `18`;
- final packets: `8092`;
- final valid events: `7902`;
- final ignored events: `190` (`non_ip`);
- final dropped events: `0`;
- final readiness: `FORECAST_READY`;
- final forecast status: `READY`;
- final state buffer: `10`;
- five horizons were present: `+10/+20/+30/+40/+50`;
- threshold observed: `0.19`.

The Phase L baseline wrapper failure (`Host live API did not start on port 8005`) and one 10-second `/api/v1/live` timeout were investigated and corrected in Phase M. The corrected wrapper result is recorded in [`PHASE_M_WRAPPER_FIX_REPORT.md`](PHASE_M_WRAPPER_FIX_REPORT.md). Phase L’s Docker/TLS/multi-host limitations remain unchanged.

## 8. Live soak

**PASS** — bounded real local capture run of `301.79` seconds (about 5 minutes), with no request errors in the direct observation loop.

Observed during that run:

- requests: `56`;
- request errors: `0`;
- peak packets: `8068`;
- peak completed flows: `27`;
- peak valid states: `27`;
- peak forecast updates: `18`;
- buffer remained bounded at the required history size (`10` at the final state);
- p95 `/api/v1/live` latency: `2483.79 ms`;
- final dropped events: `0`.

**NOT VERIFIED** — 15-minute, 30-minute, and longer soak runs. CPU/RAM telemetry was not captured during the valid live run, so no leak-free or production-capacity claim is made. Five-sensor soak is also **NOT VERIFIED**.

## 9. Outage/recovery

**PASS** — automated retry, buffering, stale-state, and lifecycle contract tests passed.
**NOT VERIFIED** — a real central outage with a physically deployed agent, network reconnection, and buffer flush.

## 10. Central restart and forecast rebuild

**PASS** — local API health/readiness and process-local lifecycle semantics are covered by the automated suite.
**NOT VERIFIED** — Docker down/up or real central restart with multiple remote agents, registry persistence, reconnect, and post-restart forecast rebuild.

The observed local stop state correctly reported `LIVE_STOPPED` / stale readiness after capture stopped. Historical runtime continuity is not claimed.

## 11. Credential lifecycle and spoofing

**PASS** — automated authentication, sensor identity, credential binding, revocation, and spoofing contract tests passed.
**NOT VERIFIED** — a live operator-driven credential revocation and two-host spoofing exercise over a real TLS deployment.

## 12. Stale telemetry and backend outage

**PASS** — automated state/forecast lifecycle coverage exists for stale telemetry and backend error semantics.
**NOT VERIFIED** — browser observation against a deployed remote sensor during those failures.

The product distinguishes backend unavailability from sensor state in its contract; this distinction was not promoted to a physical staging claim.

## 13. Frontend real-sensor validation

**PASS** — frontend typecheck and production build passed.
**NOT VERIFIED** — browser validation of Overview, Sensors, Sensor Detail, Agent Health, Telemetry Health, K=5 forecast display, and sensor switching against real running sensors.

## 14. Operator journey

**PASS** — operator documentation and CLI/package paths are present and release-audit checked.
**NOT VERIFIED** — the complete new-operator journey from package installation through remote registration, live heartbeat, telemetry, forecast, stop, and recovery on separate hosts.

## 15. Resource observations

The valid direct live loop established no request errors, no dropped events, a final bounded history buffer of `10`, and finite observed completed-flow/state counts. It did not record a valid live CPU/RAM time series, queue depth, log growth, or registry growth. Therefore:

- memory leak: **NOT VERIFIED**;
- CPU stability: **NOT VERIFIED**;
- queue/flow-table unbounded growth: **NOT VERIFIED**;
- connection/thread/process leak: **NOT VERIFIED**;
- 5-sensor resource behavior: **NOT VERIFIED**.

The p95 live API latency of `2483.79 ms` is a measured local observation, not a performance SLO.

## 16. Security observations

**PASS** — the prior public security audit, secret/path/link scans, and automated security tests passed. No new runtime artifact or credential was added in this phase.
**NOT VERIFIED** — central/agent audit logs from a real TLS multi-host deployment, including production proxy logs and certificate-failure paths.

## 17. Model integrity

**PASS** — frozen model/data paths were not modified; the protected diff remained empty. The release contract remains 17 features, `L=10`, `K=5`, target unchanged, threshold `0.19`.

## 18. Package validation

**PASS** — exact carried-forward evidence:

- wheel and sdist build passed;
- clean wheel import/CLI smoke passed;
- `sentinel-agent --version` returned `sentinel-agent 0.2.0`;
- `pip check` passed;
- Python installation checks passed.

## 19. Documentation and release audit

**PASS** — release audit, secret scan, path scan, link scan, and `git diff --check` passed in the preceding release-candidate validation. Documentation explicitly retains the unavailable-infrastructure boundaries.

## Exact PASS items

- local environment inventory for Windows/Python/Npcap/Wi-Fi;
- Compose configuration syntax;
- package build and clean wheel/CLI smoke;
- pip dependency consistency;
- automated authentication, agent, telemetry, buffering, stale-state, and lifecycle contracts;
- local central API health/readiness;
- 10-second real packet-capture smoke;
- approximately 5-minute real local capture/forecast observation;
- release, secret, path, link, and diff checks;
- model/data contract integrity.

## Exact FAIL items observed in the Phase L baseline

- the spawned-server path of `scripts/run_live_rc_validation.ps1` failed to detect the API within its startup window;
- one existing-server wrapper `/api/v1/live` request exceeded its 10-second timeout during the attempted wrapper run.

These historical baseline failures were fixed and revalidated in Phase M; they are retained here for traceability.

## Exact NOT VERIFIED items

- Docker runtime, restart, down/up recovery, and registry persistence;
- real staging TLS, certificate chain, hostname verification, and reverse proxy;
- physical remote-agent installation and networked registration;
- physical multi-host isolation;
- 15-minute/30-minute live soak;
- five-sensor soak;
- physical central outage, sensor failure, restart, credential revocation, and spoofing;
- browser validation with real sensors;
- full operator journey on deployed hosts;
- production resource/leak behavior.

## Exact blockers

1. Docker Desktop daemon is not running on the validation host.
2. No staging hostname, TLS certificate chain, or reverse proxy is available.
3. No second physical host is available for remote/multi-sensor validation.
4. The valid live run was approximately five minutes, not the requested 30-minute soak, and did not capture CPU/RAM time series.

## Final readiness classification

**OPEN-SOURCE RELEASE READY WITH ENVIRONMENT VALIDATION PENDING**

This classification is intentionally below staging or production readiness. It means the repository/package can be released as an open-source V0.1 candidate with explicit setup limitations, but this evidence does not support a staging-ready or production-ready claim.
