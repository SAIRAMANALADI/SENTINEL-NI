# Deployment Guide

## Local installation

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.lock.txt

`requirements.lock.txt` is the reproducible release path. The compatible-range
`requirements.txt` file remains available for development and platform-specific
dependency resolution.

## Start backend

    $env:SIH_TELEMETRY_MODE = "mock"
    python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000

Verify with GET /api/v1/health and GET /api/v1/ready.

## Start dashboard

In another terminal:

    $env:SIH_API_URL = "http://127.0.0.1:8000"
    python -m streamlit run app\streamlit_app.py

Select Full Integrated Demo. The dashboard calls the backend demo endpoint;
the backend composes the existing engine.

## Docker Compose

    docker compose up --build

The compose stack contains backend and dashboard, mounts model/config/demo
artifacts read-only, and writes audit output to the local ignored results path.
Raw/processed datasets and PCAPs are not copied into the image.

## Authenticated development

Set SIH_AUTH_ENABLED=true and inject role tokens through the environment. Use
Authorization: Bearer token. Do not put tokens in compose files, source, or
logs.

For production, set `SIH_ENV=production`, `SIH_AUTH_ENABLED=true`, and all
viewer/operator/admin role tokens through a secret manager or protected
environment. Production requires HTTPS with certificate verification; do not
use `curl -k`, `verify=False`, or an equivalent bypass.

Set `SIH_TRANSPORT_MODE=direct_https` when the application itself is the
secure listener. When TLS terminates at a private reverse proxy, set
`SIH_TRANSPORT_MODE=trusted_proxy` and configure
`SIH_TRUSTED_PROXY_CIDRS` to the proxy's exact source IP/CIDR. The API rejects
direct HTTP and ignores forged forwarded-protocol headers from untrusted
peers. It returns `403 HTTPS_REQUIRED` rather than redirecting authenticated
API or telemetry requests. Only loopback health/readiness probes may use
internal HTTP.

## Remote sensor deployment

The central service accepts aggregated, versioned network states. A remote
server runs the sensor locally; it does not send raw packets or ask the
central service to capture the remote interface.

1. Start the central backend with HTTPS provided by a private reverse proxy,
   a firewall/private network, and role tokens configured in the environment.
2. Create one short-lived enrollment credential as an administrator:

    `$headers = @{ Authorization = "Bearer $env:SIH_ADMIN_TOKEN" }`
    `$body = @{ expires_in_seconds = 600 } | ConvertTo-Json`
    `Invoke-RestMethod -Method Post -Uri https://sentinel.example.internal/api/v1/sensors/enrollment -Headers $headers -Body $body -ContentType application/json`

3. On the connected server, install the package and initialize the agent:

    `python -m src.agent init --server-url https://sentinel.example.internal --interface "Ethernet" --environment production`
    `python -m src.agent register --enrollment-token <one-time-token>`
    `python -m src.agent start`

Registration gives the agent a persistent sensor ID and dedicated runtime
credential. The runtime credential is stored locally and is never written to
logs. The agent converts packets into completed flows and the existing
10-second, 17-feature state contract, batches states, retries delivery, and
stores unsent batches in a bounded disk buffer. It never forwards raw payloads.
Use `python -m src.agent stop` for a best-effort local stop; use a service
manager for production process supervision.

Credential rotation is admin-only:

    `Invoke-RestMethod -Method Post -Uri https://central-host/api/v1/sensors/<sensor-id>/rotate-credential -Headers @{ Authorization = "Bearer $env:SIH_ADMIN_TOKEN" }`

Deliver the returned credential out of band, update the agent's protected
credential store, and restart it. The old credential is invalid immediately;
there is no automatic rotation or grace period.

The agent observes traffic in parallel with the customer's application. It is
not a reverse proxy and customer requests do not wait for telemetry delivery.
Run `python -m src.agent status` to read the agent's local buffer and the
authenticated sensor-scoped central status. Run the central API behind a TLS
reverse proxy/private network; do not expose port 8000 directly to the public
internet.

Reliability operations are documented in `docs/SENSOR_RELIABILITY.md`. The
central status intentionally reports Agent, Telemetry, and Forecast separately.
The central JSON registry persists sensor identity on the Compose host-backed
registry mount, but
remote L=10 runtime history remains process-local and must rebuild after a
central restart. Docker Compose does not grant host packet-capture capability;
the agent must run on the monitored host.

## Historical Phase I validation boundary

The following section records the older Phase I boundary and is retained for
historical traceability. It is superseded for the current candidate by
[`PHASE_T_PUBLIC_RELEASE_CANDIDATE_REPORT.md`](PHASE_T_PUBLIC_RELEASE_CANDIDATE_REPORT.md).

At Phase I, the repository's deployment validation was **development-only**:

- **Tested:** local Python/package installation, automated agent-to-central
  delivery, sensor isolation, buffering/retry contracts, security checks,
  frontend typecheck/build, and `docker compose config`.
- **Supported but not tested in this workspace:** a real reverse-proxy HTTPS
  deployment, two physical remote hosts, Docker container startup/restart,
  live packet-capture soak, and a five-sensor/30-minute run.
- **Planned:** staging certificate/DNS validation, physical multi-host soak,
  measured outage recovery, and production-capacity assessment.

The historical warning remains valid for staging claims: do not infer public
staging support from Compose configuration alone. Current local runtime and
isolated TLS evidence is recorded in the Phase T report.

### Multi-sensor runtime limits

Central fleet summaries are available at `GET /api/v1/sensors`; full detail and
forecast reads require an explicit sensor ID. Set `SIH_MAX_SENSOR_COUNT` to a
positive bound appropriate for the deployment (default: `1024`). This bounds
the in-process remote runtime registry; it is not a replacement for a shared
multi-worker state store.

The registry persists sensor identity, but remote state histories and forecasts
are process-local. After a central restart, sensors must reconnect and supply
ten contiguous valid states before their forecast becomes available again.
Use the operator-only disable endpoint to revoke a sensor while retaining its
identity and audit record. Do not expose the API directly to the public
internet; terminate TLS and enforce the existing viewer/operator credentials
at the deployment boundary.

## Phase Q validation record

Local Compose, a real Nginx TLS proxy, an actual agent, live Wi-Fi capture,
central outage buffering/recovery, and independent customer-path behavior were
validated on 2026-09-04. Physical multi-host, five-sensor, L=10 forecast
readiness, expired-certificate behavior, and 30-minute soak remain
**NOT VERIFIED**. This record does not qualify a local run as staging.

## Phase R remote forecast record

The 2026-09-04 real-agent run validated HTTPS registration, heartbeat, live
Wi-Fi/Npcap capture, telemetry delivery, central outage buffering/retry/flush,
agent OFFLINE/STALE transitions, same-identity restart, and customer-path
isolation. The central API rejected duplicate or gapped 10-second timestamps,
and the sensor ended below the required contiguous `L=10` history. A live
`K=5` LSTM forecast and forecast-ready dashboard were therefore **NOT VERIFIED**.

Do not treat the local Compose/TLS exercise as staging. Physical multi-host and
five-sensor behavior, expired-certificate handling, a 30-minute soak, and live
capacity remain unverified. See
[`PHASE_R_REMOTE_FORECAST_REPORT.md`](PHASE_R_REMOTE_FORECAST_REPORT.md).

## Phase T current release-candidate record

The current candidate also validates local Compose health/restart/down-up,
browser smoke, clean wheel installation, release-audit links, and the real
Windows remote path reaching contiguous `L=10` and existing `K=5` inference.
The complete evidence and remaining unverified gates are in
[`PHASE_T_PUBLIC_RELEASE_CANDIDATE_REPORT.md`](PHASE_T_PUBLIC_RELEASE_CANDIDATE_REPORT.md).
