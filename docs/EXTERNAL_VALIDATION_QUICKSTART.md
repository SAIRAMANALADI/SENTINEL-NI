# Sentinel External Validation Quickstart

This is the shortest clean-checkout path for an independent validator. Record
commands, timestamps, safe status output, and failures in
[`EXTERNAL_VALIDATION_RESULT_TEMPLATE.md`](EXTERNAL_VALIDATION_RESULT_TEMPLATE.md).
Never record tokens, private keys, PCAP contents, customer payloads, or private
filesystem paths. Sentinel observes out of band; customer requests continue to
reach the customer application directly.

## Prerequisites

- A clean checkout and Python 3.14.
- Node.js/npm for the Next dashboard, or Docker Compose.
- A central host and a monitored sensor host with outbound HTTPS.
- Npcap on Windows or libpcap on Linux, with permission to capture the chosen
  interface.
- Three dashboard/Central role tokens supplied through protected environment
  injection, plus a one-time sensor enrollment token from an administrator.
- A TLS endpoint whose hostname matches its certificate. Local HTTP is for
  development only.

## Installation and Central startup

From the repository root:

```powershell
py -3.14 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
# If a supplied wheel is not available, build the candidate from this checkout:
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
& .\.venv\Scripts\python.exe -m build --wheel --sdist
& .\.venv\Scripts\python.exe -m pip install --no-deps .\dist\sih26_26153-0.1.0-py3-none-any.whl
& .\.venv\Scripts\python.exe -m pip check
& .\.venv\Scripts\sentinel-agent.exe --version
& .\.venv\Scripts\sentinel-agent.exe --help
```

For the sensor-host commands below, activate the environment that contains the
installed wheel first, or replace `sentinel-agent` with that environment's
full executable path.

Start Central in a second terminal. Inject `SIH_ENV=production`,
`SIH_AUTH_ENABLED=true`, all three `SIH_*_TOKEN` values, and the documented
transport settings through the environment or secret manager. Use
`SIH_TRANSPORT_MODE=direct_https` when the application terminates TLS itself;
for a reverse proxy, use `SIH_TRANSPORT_MODE=trusted_proxy` and the exact
`SIH_TRUSTED_PROXY_CIDRS` value described in [`TLS_DEPLOYMENT.md`](TLS_DEPLOYMENT.md):

```powershell
& .\.venv\Scripts\python.exe -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000
```

The command above is the private HTTP upstream for the documented trusted
reverse-proxy topology. If Uvicorn terminates TLS directly, provide the
certificate and key explicitly:

```powershell
& .\.venv\Scripts\python.exe -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --ssl-certfile <certificate-path> --ssl-keyfile <private-key-path>
```

The Compose command below is a local/container platform smoke path; it does
not terminate public TLS. For internet-facing validation, keep its backend and
legacy Streamlit ports private and place a real TLS reverse proxy in front of
the authenticated Next frontend, with the production transport settings above.

On a Linux sensor host, the equivalent installation/CLI setup is:

```sh
python3.14 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.lock.txt
python -m pip install --no-deps ./dist/sih26_26153-0.1.0-py3-none-any.whl
python -m pip check
sentinel-agent --version
sentinel-agent --help
```

Verify health/readiness through the configured HTTPS endpoint:

```powershell
Invoke-RestMethod https://<central-host>/api/v1/health
Invoke-RestMethod https://<central-host>/api/v1/ready
```

## Dashboard startup and authentication

For local frontend development, from `frontend/` run `npm ci` and `npm run dev`.
For the documented container path, run `docker compose up -d --build`.
Production dashboard configuration must set `SIH_DASHBOARD_AUTH_ENABLED=true`,
`SIH_AUTH_ENABLED=true`, `SIH_ENV=production`, and the same role tokens in the
frontend and Central environments. Open the HTTPS dashboard in a fresh private
browser context. For external access, expose only the authenticated Next
frontend (port 3000) through TLS. Keep the legacy Streamlit surface (port 8501)
loopback/private; it is not the end-user dashboard authentication boundary.

Confirm the sign-in screen appears, submit an invalid token once, then sign in
with the viewer token. Verify Forecast, Sources, and System render. Confirm the
browser stores only the opaque session cookie and that a viewer cannot invoke
Demo or Live start/stop. Sign out and confirm dashboard data routes return to
unauthorized state. Repeat the control checks with an operator token; admin
inherits operator access and may perform the documented enrollment request.

## Sensor creation and agent registration

Using an admin Central credential, create a one-time enrollment token. Do not
paste the token into evidence:

```powershell
$headers = @{ Authorization = "Bearer $env:SIH_ADMIN_TOKEN" }
$body = @{ expires_in_seconds = 600 } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri https://<central-host>/api/v1/sensors/enrollment -Headers $headers -Body $body -ContentType application/json
```

Transfer the one-time token out of band to the sensor host. On that host:

```text
sentinel-agent init --server-url https://<central-host> --interface "<exact-interface>" --environment production
sentinel-agent register --enrollment-token <one-time-token>
sentinel-agent config validate
sentinel-agent start
```

In another sensor-host terminal run `sentinel-agent status` and
`sentinel-agent diagnostics`. The dashboard must show the sensor as `ONLINE`
only after a fresh heartbeat and accepted telemetry. Record the sensor ID only,
not its runtime credential.

## Capture, L=10, and K=5

Confirm the exact capture interface and required Npcap/libpcap permission. Keep
the agent running until the selected sensor shows fresh telemetry and contiguous
history `10 / 10`. Confirm the existing LSTM path returns exactly five future
horizons at +10s, +20s, +30s, +40s, and +50s. In the dashboard verify the five
forecast rows, the unchanged threshold/model contract, source evidence wording,
and recommendation-only mitigation wording. A Forecast Score is not a
probability and a Candidate Source is not an attacker attribution.

## Restart, outage, and customer-path checks

Run `sentinel-agent stop`, then `sentinel-agent restart`; verify the same sensor
identity returns and record any expected OFFLINE/STALE transition. Stop Central,
observe bounded retry/buffering, restart Central, and record recovery without
claiming delivery during the outage. While Central is stopped, issue a request
to the independently deployed customer application endpoint; confirm that the
customer response remains available and was not routed through Sentinel.

## Evidence checklist

Record the validator/date, OS/Python/browser, Central and sensor hosts, network,
Docker/TLS mode, exact safe commands, status output, timestamps, screenshots
without credentials, and every failure. Mark each result `PASS`, `FAIL`, or
`NOT TESTED`. Remove private data before submitting the completed result
template.

## Troubleshooting

- `production sensor transport requires https`: use a certificate-valid HTTPS
  central URL.
- `agent is not registered`: obtain a fresh one-time enrollment token and run
  `register` once.
- `capture interface not found` or capture unavailable: inspect exact host
  interface names and install/grant Npcap/libpcap permission.
- `UNREACHABLE` or `DEGRADED`: check Central health, outbound firewall rules,
  TLS trust, and `sentinel-agent diagnostics`.
- Dashboard `401`: sign in again or confirm the session cookie and matching
  dashboard/Central role-token configuration; do not send a bearer token from
  browser JavaScript.
- Forecast remains waiting: confirm fresh accepted telemetry and contiguous
  `10 / 10` history rather than replay/mock mode.

## Report format

Submit the completed
[`EXTERNAL_VALIDATION_RESULT_TEMPLATE.md`](EXTERNAL_VALIDATION_RESULT_TEMPLATE.md)
with safe evidence, exact failures, and recommended fixes. Do not call the
release externally validated until an unrelated environment has completed the
required checks.
