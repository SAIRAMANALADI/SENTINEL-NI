# Operator Quickstart

Sentinel is an out-of-band monitoring service. The customer's application
continues to receive requests directly; a local or remote sensor observes
traffic in parallel and sends aggregate telemetry to Central Sentinel.

## 1. Start Central Sentinel locally

From a clean checkout with Python 3.12–3.14:

```powershell
py -3.14 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
$env:SIH_ENV = "development"
$env:SIH_TELEMETRY_MODE = "mock"
& .\.venv\Scripts\python.exe -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000
```

In a second terminal, verify the service:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
Invoke-RestMethod http://127.0.0.1:8000/api/v1/ready
```

For the containerized central path, use `docker compose up -d --build`. Local
Compose startup, health, restart, and down/up were validated for this release
candidate. This remains local runtime evidence, not public staging capacity.

## 2. Open the dashboard

For the Next.js dashboard:

```powershell
Set-Location frontend
npm ci
npm run dev
```

Open `http://localhost:3000`. The Streamlit fallback can be started from the
repository root with `python -m streamlit run app\streamlit_app.py`.

## 3. Create a sensor enrollment credential

Use the central administrator credential. In a development profile with
authentication disabled, omit the `Authorization` header. In an authenticated
deployment, set `SIH_ADMIN_TOKEN` through the environment and use:

```powershell
$headers = @{ Authorization = "Bearer $env:SIH_ADMIN_TOKEN" }
$body = @{ expires_in_seconds = 600 } | ConvertTo-Json
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/sensors/enrollment `
  -Headers $headers -Body $body -ContentType application/json
```

Use HTTPS and the private deployment hostname outside local development.
Treat the returned one-time enrollment token as a secret and transfer it
out-of-band to the monitored server.

## 4. Install and register the remote agent

Build or obtain the release wheel, then install it on the monitored server:

```powershell
python -m pip install .\dist\sih26_26153-0.1.0-py3-none-any.whl
sentinel-agent --version
sentinel-agent init --server-url https://sentinel.example --interface "Ethernet" --environment production
sentinel-agent register --enrollment-token <one-time-enrollment-token>
sentinel-agent config validate
```

Use the exact interface name discovered on that server. Production mode
requires HTTPS; do not put the runtime credential in a command, URL, source
file, or log.

## 5. Start and verify the sensor

```text
sentinel-agent start
```

The command runs in the foreground. In another terminal, use:

```text
sentinel-agent status
sentinel-agent diagnostics
```

The diagnostics command is the supported first-run doctor equivalent. It
reports platform, versions, capture availability, endpoint/TLS state,
registration state, storage, and connection status without returning secrets.

## 6. Select and observe the sensor

In the dashboard, open **Sensors**, select the sensor by hostname/identity,
and check these separately:

- Agent Health: process status and agent version.
- Telemetry Health: heartbeat, last telemetry, sequence, and buffer state.
- Forecast Health: whether enough valid states exist for the L=10 history.

Forecast becomes available only after sufficient valid telemetry. A predictive
warning is an operating-policy result from the +10s Forecast Score; it is not
confirmation of an attack and is not a calibrated probability.

If the sensor disconnects, inspect `sentinel-agent status`, `diagnostics`, the
central sensor detail, and the bounded local buffer. Restart with
`sentinel-agent restart` after correcting the endpoint, credential, capture
permission, or interface problem.

## Deployment boundary

Sentinel does not proxy, block, or delay customer requests. The application
path remains separate from sensor observation and telemetry delivery.
