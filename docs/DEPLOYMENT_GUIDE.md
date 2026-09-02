# Deployment Guide

## Local installation

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt

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

## Remote sensor deployment

The central service accepts aggregated, versioned network states. A remote
server runs the sensor locally; it does not send raw packets or ask the
central service to capture the remote interface.

1. Start the central backend with HTTPS provided by a private reverse proxy,
   a firewall/private network, and role tokens configured in the environment.
2. Create one short-lived enrollment credential as an administrator:

    `$headers = @{ Authorization = "Bearer $env:SIH_ADMIN_TOKEN" }`
    `$body = @{ expires_in_seconds = 600 } | ConvertTo-Json`
    `Invoke-RestMethod -Method Post -Uri http://central-host:8000/api/v1/sensors/enrollment -Headers $headers -Body $body -ContentType application/json`

3. On the connected server, install the package and initialize the agent:

    `python -m src.agent init --server-url https://central-host --interface "Ethernet" --environment production`
    `python -m src.agent register --enrollment-token <one-time-token>`
    `python -m src.agent start`

Registration gives the agent a persistent sensor ID and dedicated runtime
credential. The runtime credential is stored locally and is never written to
logs. The agent converts packets into completed flows and the existing
10-second, 17-feature state contract, batches states, retries delivery, and
stores unsent batches in a bounded disk buffer. It never forwards raw payloads.
Use `python -m src.agent stop` for a best-effort local stop; use a service
manager for production process supervision.

The agent observes traffic in parallel with the customer's application. It is
not a reverse proxy and customer requests do not wait for telemetry delivery.
Run `python -m src.agent status` to read the agent's local buffer and the
authenticated sensor-scoped central status. Run the central API behind a TLS
reverse proxy/private network; do not expose port 8000 directly to the public
internet.

Reliability operations are documented in `docs/SENSOR_RELIABILITY.md`. The
central status intentionally reports Agent, Telemetry, and Forecast separately.
The central JSON registry persists sensor identity on the Compose volume, but
remote L=10 runtime history remains process-local and must rebuild after a
central restart. Docker Compose does not grant host packet-capture capability;
the agent must run on the monitored host.
