# External Validation Guide

This guide is for the first users evaluating Sentinel / NI from a public
source release. Please report observed behavior rather than proposing broad
features without evidence.

For the shortest executable path, use
[`EXTERNAL_VALIDATION_QUICKSTART.md`](EXTERNAL_VALIDATION_QUICKSTART.md) and
record results in [`EXTERNAL_VALIDATION_RESULT_TEMPLATE.md`](EXTERNAL_VALIDATION_RESULT_TEMPLATE.md).

## DO NOT USE DEVELOPMENT MACHINE

The validator must use an unrelated machine, network, VM, or independently
controlled host. Do not count another process, browser, user, replay, mock
telemetry, or container on the implementation machine as independent
validation. Record the exact candidate commit or artifact SHA256 before
testing and keep the candidate unchanged throughout the run.

## Before reporting

Record the project release (`0.1.0`), agent version (`0.2.0`), OS, Python
version, deployment mode, telemetry source, and the exact command or dashboard
page involved. Remove tokens, credentials, private traffic, PCAP contents,
personal paths, and unrelated customer data.

## What to report

- Installation or package problems: command, platform, Python version, and
  complete safe error output.
- Sensor registration or heartbeat problems: central deployment, agent
  configuration shape (not the credential), status output, and timestamps.
- Capture compatibility: OS, Npcap/libpcap version, interface type, privilege
  setup, and whether packets/flows/states were observed.
- Telemetry problems: sensor status, sequence/error messages, buffer behavior,
  and whether the central endpoint was reachable.
- Forecast problems: history length, freshness, displayed Forecast Score,
  horizon timestamps, and whether the state was replay, local live, or remote.
- Dashboard problems: route, selected sensor, visible health state, browser,
  and safe screenshot or console excerpt.
- Resource usage: duration, approximate CPU/memory, packet/flow rate, buffer
  depth, and whether forecast updates continued.

## Safe feedback loop

```text
INSTALL -> CONNECT SERVER -> RUN SENSOR -> OBSERVE TELEMETRY
        -> REPORT REPRODUCIBLE ISSUE -> REPRODUCE -> FIX -> TEST -> PATCH
```

Use the public issue templates for bugs, deployment issues, and scoped feature
requests. Use the private advisory process in [`../SECURITY.md`](../SECURITY.md)
for vulnerabilities;
do not disclose security details in a public issue.

## Validation protocol

Run this matrix from a clean checkout and record the exact command, result,
environment, and safe evidence. A local pass is not an external pass.

Before opening an internet-facing dashboard, set
`SIH_DASHBOARD_AUTH_ENABLED=true`, `SIH_AUTH_ENABLED=true`, and inject all
three role tokens through a secret manager or protected environment. Confirm
that an anonymous browser receives no dashboard data, sign in with a viewer
token, verify read-only pages work, verify a viewer cannot invoke live/demo
actions, verify an operator can invoke the documented operator actions, and
verify sign-out or session expiry removes access. Do not record any token.

| Step | Protocol check | Current local evidence | External requirement |
| --- | --- | --- | --- |
| A | Install wheel and verify CLI | **VERIFIED LOCALLY** — non-editable wheel smoke | Clean dependency-inclusive venv |
| B | Start Central and check health/readiness | **VERIFIED LOCALLY** — Python and Compose | Independent clean checkout |
| C | Start/open dashboard | **VERIFIED LOCALLY** — build and browser smoke | Independent browser/session |
| D | Add/create a sensor | **VERIFIED LOCALLY** — real onboarding path | Independent operator run |
| E | Initialize/register Agent | **VERIFIED LOCALLY** — real Windows Agent path | External OS/capture backend |
| F | HTTPS telemetry | **VERIFIED LOCALLY** — isolated TLS proxy | Trusted external TLS endpoint |
| G | Heartbeat and ONLINE state | **VERIFIED LOCALLY** | External central/sensor pair |
| H | Live capture | **VERIFIED LOCALLY** — Windows/Npcap | Linux/libpcap or another supported host |
| I | Contiguous `L=10` history | **VERIFIED LOCALLY** | External traffic run |
| J | Existing LSTM `K=5` forecast | **VERIFIED LOCALLY** — five horizons | External traffic run |
| K | Dashboard rendering and source/mitigation semantics | **VERIFIED LOCALLY** | Independent browser review |
| L | Agent stop/restart/recovery | **VERIFIED LOCALLY** — Windows stop and restart | External service/supervisor run |
| M | Central outage buffering/retry/flush | **VERIFIED LOCALLY** in prior real-path evidence | Independent outage exercise |
| N | Customer request-path independence | **VERIFIED LOCALLY** during central outage | Independent customer application |
| O | Dashboard authorization: anonymous denied, viewer read-only, operator/admin controls, logout and expiry invalidation | **NOT VERIFIED EXTERNALLY** — local runtime smoke only | Independent HTTPS deployment |
| P | Linux agent: physical libpcap capture, exact interface/permissions, systemd start/status, reboot recovery | **NOT VERIFIED** | Linux host |
| Q | Multi-host: two physical hosts, five independent sensors, unique identities, isolated histories/forecasts | **NOT VERIFIED** | Two-host deployment |
| R | 30-minute soak: CPU, memory, rates, queue depth, errors, logs, and forecast latency | **NOT VERIFIED** | Capacity test environment |

## Executable A–N protocol

Run these checks from a clean checkout. Replace angle-bracket values with
operator-owned values and never paste credentials into issue reports.

| Step | Minimum action and evidence to record |
| --- | --- |
| A | Create a fresh Python 3.14 venv, install `requirements.lock.txt`, install the supplied release wheel with `--no-deps`, run `pip check`, then run `sentinel-agent --version` and `--help`. If no wheel was supplied, install `requirements-dev.txt` and build `py -m build --wheel --sdist` first. Separately install the published wheel in a clean venv and repeat the CLI smoke. |
| B | Start Central with `python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000`; verify `GET /api/v1/health` is 200 and record `/api/v1/ready` status/body. |
| C | Start the documented frontend or Compose stack, open local `http://localhost:3000` for local evidence, and separately use the external HTTPS endpoint for dashboard authentication/session evidence. Record the Overview, System, and browser-console result without tokens. |
| D | Use the documented admin enrollment request, then confirm the dashboard Add Sensor page explains that browser enrollment is not the authority; do not put the enrollment token in evidence. |
| E | On the sensor host run `sentinel-agent init --server-url <https-url> --interface <interface> --environment production`, register with the one-time enrollment token, and record only the sensor ID and safe status output. |
| F | Confirm the agent sends `POST /api/v1/telemetry` over HTTPS with its sensor token and that HTTP/plaintext or an untrusted CA is rejected. |
| G | Run `sentinel-agent status`; verify Central reports fresh heartbeat and transitions the sensor to `ONLINE` only after fresh heartbeat and telemetry. |
| H | Start capture using the exact interface and required Npcap/libpcap privileges; record adapter status, packet/flow/state counters, and any permission error. |
| I | Continue until the selected sensor reports contiguous history `10 / 10`; record timestamps and whether any gap reset the history. |
| J | Confirm the existing LSTM path returns exactly five horizons (+10s through +50s); record model/contract identifiers, not raw traffic. |
| K | In the dashboard inspect Forecast, Sources, and Mitigation. Confirm source rows are evidence-scoped, warnings are not attack confirmation, and mitigation says simulation-only. |
| L | Stop and restart the agent with `sentinel-agent stop` and `sentinel-agent restart`; record OFFLINE/STALE and recovery of the same sensor identity. |
| M | Stop Central, continue the agent long enough to observe bounded buffering/retry, restart Central, and record flush/recovery without claiming delivery during the outage. |
| N | Run an independent customer HTTP request while Central is stopped; record that the customer response remains available and that no request is routed through Sentinel. |

### Dashboard authorization sequence

1. Start the dashboard with the production environment settings above behind
   the documented TLS endpoint.
2. Open the dashboard in a fresh private browser context and confirm the sign-in
   screen appears without a Central data request being exposed to the browser.
3. Submit an invalid token and confirm a generic rejection without token echo.
4. Sign in with the viewer token; confirm Forecast, Sources, and System render.
5. Confirm a viewer POST to demo/live start/live stop is rejected.
6. Sign in with the operator token; confirm the documented demo/live actions
   work and the browser still has only the opaque cookie.
7. Sign out, then confirm the sign-in screen returns and data routes reject the
   old session. Repeat after the configured TTL in a controlled test.

### Status boundaries

**VERIFIED LOCALLY:** Windows/Npcap real remote forecast path; central API,
dashboard, Docker lifecycle, isolated TLS, browser journey, CLI lifecycle,
customer-path outage isolation, package build, and automated regression checks.

**NOT VERIFIED LOCALLY:** TruffleHog, dependency-inclusive clean installation,
physical Linux capture/service boot, physical multi-host/five-sensor operation,
30-minute soak/resource series, expired certificate, public DNS/ingress, and
public CA deployment.

**REQUIRES EXTERNAL ENVIRONMENT:** An unrelated developer completing the full
protocol, a second physical host, Linux/libpcap operation, public TLS ingress,
long-running capacity measurement, and any claim of public-user adoption.

For a complete run, start at README, use only documented commands, capture
safe timestamps for registration/heartbeat/telemetry/forecast readiness, and
record every confusing or missing step. Do not report a simulated Replay run
as live capture evidence.

## Scope reminder

Sentinel is out-of-band: customer requests do not pass through Sentinel. A
Forecast Score is not a calibrated probability, Candidate Sources are not
attacker attribution, and Mitigation Recommendations are simulation-only.
Physical multi-host, public ingress, expired certificates, long soak, and
physical Linux capture remain environment-dependent validation work.
