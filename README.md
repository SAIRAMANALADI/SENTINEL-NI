# SENTINEL / NI

## Network intelligence for the next 50 seconds

Sentinel / NI is an open-source network-security platform for short-horizon
network-state forecasting. It converts measured network activity into fixed
10-second states, applies a frozen LSTM model, and presents a focused operator
workflow: Forecast Score, Predictive Warning, Candidate Sources, and
Mitigation Recommendations.

It is built for decision support. It does not claim confirmed intrusion
detection, automatic blocking, or calibrated risk probabilities.

| Release contract | Current implementation |
| --- | --- |
| State interval | 10 seconds |
| Model context | 10 states (L=10) |
| Forecast | Five direct horizons (K=5): +10s to +50s |
| Model inputs | 17 numeric flow-derived features |
| Primary threshold | 0.19 |
| Response model | Recommendation-only; simulation-only mitigation |
| Modes | Replay, Mock, Local Live, Remote Sensor |

## Operating model

Sentinel operates out of band. It is not a reverse proxy, does not sit between
customers and an application, and must not delay customer requests.

    Customer
       |
       v
    Company Application Server  ------------------------------> Response
       |
       | observed in parallel
       v
    Sentinel Sensor / Agent
       |
       | authenticated, aggregated telemetry
       v
    Central Sentinel
       |
       +--> 10-second state runtime
       +--> frozen LSTM K=5
       +--> operating policy
       +--> source intelligence where telemetry supports it
       +--> mitigation recommendations
       v
    Dashboard

The remote agent processes traffic on its own host, builds the approved state
schema locally, and sends bounded state batches to the central API. It never
forwards raw packet payloads. The browser communicates only with Central
Sentinel, never directly with remote agents.

## What Sentinel provides

| Capability | Behaviour |
| --- | --- |
| Forecast | Five future Forecast Scores for +10/+20/+30/+40/+50 seconds |
| Warning | Predictive Warning when the +10s score meets the configured threshold |
| Candidate Sources | Evidence-based ranking from source-capable local telemetry; not attacker attribution |
| Mitigation | Human-reviewed recommendations only; no firewall changes or automatic blocking |
| Replay | Deterministic local demonstration and regression mode |
| Local Live | Host-level metadata capture with Scapy and Npcap/libpcap prerequisites |
| Remote Sensor | Per-server enrollment, heartbeat, telemetry validation, isolated histories, and sensor-scoped forecasts |

## Quick start

### Run the central platform

#### Docker Compose

Use Docker Compose for the central API and dashboard only. It does not claim
arbitrary host packet capture from inside a container.

    docker compose up -d --build

Open the primary dashboard at [http://localhost:3000](http://localhost:3000).
The central API listens on port 8000; the Streamlit fallback listens on 8501.

    docker compose down

#### Local Python

    py -3.14 -m venv .venv
    & .\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
    & .\.venv\Scripts\python.exe scripts\check_environment.py
    & .\.venv\Scripts\python.exe -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000

For local frontend development, start a second terminal:

    Set-Location frontend
    npm ci
    npm run dev

### Run a deterministic replay

    python scripts/run_replay_demo.py --max-states 20 --speed 0

Replay uses approved local sample data. It does not download datasets or read
live traffic.

### Connect a remote server

Run Central Sentinel behind HTTPS, a firewall or private network, and
environment-injected credentials. Do not expose the internal application port
directly to the public internet.

An administrator creates a one-time enrollment credential through the
server-side admin API. The browser does not receive the administrator token.
On the remote server:

    python -m src.agent init --server-url https://sentinel.example --interface "Ethernet" --environment production
    python -m src.agent register --enrollment-token <one-time-enrollment-token>
    python -m src.agent start
    python -m src.agent status

The central dashboard reports registration, heartbeat freshness, telemetry
freshness, buffer depth, history readiness, and the sensor-scoped forecast. It
does not report a sensor as online merely because it was registered.

Read the [sensor installation guide](docs/SENSOR_INSTALLATION.md), the
[distributed architecture](docs/DISTRIBUTED_SENSOR_ARCHITECTURE.md), and the
[sensor security guide](docs/SENSOR_SECURITY.md) before deployment.

## Forecasting contract

The frozen target is:

    future_attack_state(t)
      = binary_attack_state(t + 10 seconds)
        within the same capture_day

The model receives exactly 17 features in the order defined by
[the feature schema](configs/state_feature_schema.yaml). It uses ten
chronological states and returns five direct forecast points. The threshold is
an operating-policy decision boundary, not a statement that a score is a
calibrated probability.

Training and evaluation use the fixed CSE-CIC-IDS2018 day-aware split:

| Role | Capture days |
| --- | --- |
| Train | 2018-02-14, 2018-02-21 |
| Validation | 2018-02-22 |
| Final test | 2018-02-28 |

The V1 state artifact contains 16,127 states. Full raw/processed datasets and
PCAP archives are intentionally not committed. The repository includes only
the small approved offline demo/test fixtures and frozen checkpoints required
to run the release checks; production datasets remain local acquisition
artifacts.

## Remote sensor architecture

Each sensor has its own identity, telemetry sequence ledger, state buffer,
forecast context, health record, and local disk buffer. Sensor histories are
never combined.

    sensor-A -> [A1, A2, A3, ...] -> forecast-A
    sensor-B -> [B1, B2, B3, ...] -> forecast-B

Remote telemetry is schema version 1 and contains a sensor ID, monotonic
sequence number, send timestamp, and up to 60 contiguous ten-second states.
The central API verifies identity, schema, feature count, finite values,
capture-day consistency, ordering, duplicate delivery, payload size, and rate
limits before the existing state and inference path is invoked.

The agent persists failed delivery batches in a bounded, sequence-ordered disk
buffer and retries transient failures with backoff. A full buffer is explicit;
the agent does not pretend unsent telemetry was delivered.

## API surface

| Area | Endpoints |
| --- | --- |
| Service | GET /api/v1/health, GET /api/v1/ready |
| Local runtime | GET /api/v1/live, GET /api/v1/telemetry |
| Forecasting | POST /api/v1/forecast, POST /api/v1/demo |
| Source and mitigation | POST /api/v1/source-priority, POST /api/v1/mitigation |
| Sensor onboarding | POST /api/v1/sensors/enrollment, POST /api/v1/sensors/register |
| Sensor operations | GET /api/v1/sensors, GET /api/v1/sensors/{sensor_id}, POST /api/v1/sensors/{sensor_id}/heartbeat |
| Remote telemetry | POST /api/v1/telemetry |

Interactive API documentation is available at /docs in development and is
disabled in production.

## Security boundaries

- Production configuration fails closed unless authentication is enabled and
  role credentials are supplied.
- Remote onboarding uses expiring, one-time enrollment credentials. Runtime
  credentials are dedicated per sensor and stored hashed centrally.
- Request validation, payload limits, per-sensor rate limits, sequence checks,
  duplicate protection, bounded buffers, and security headers are implemented.
- Packet payload content is not retained or forwarded by the live or remote
  telemetry path.
- Remote state-only telemetry cannot responsibly produce candidate-source
  attribution; the dashboard states that limitation explicitly.

Recommended topology: a private network or firewall boundary, a TLS reverse
proxy, and an authenticated Central Sentinel API. mTLS, OIDC, tenant
isolation, and high availability are future hardening work.

## Verification

The current repository verification record includes:

    python -m pytest -q       237 passed
    npm run typecheck         passed
    npm run build             passed
    docker compose config     passed

Remote-sensor coverage includes enrollment, authentication, telemetry
validation, duplicate and rate-limit handling, bounded buffering, a real
agent-to-central HTTP path reaching the LSTM, and multi-sensor runtime
isolation. See the [remote telemetry implementation report](docs/REMOTE_TELEMETRY_IMPLEMENTATION_REPORT.md)
for the exact evidence and remaining deployment work.

## Repository map

    app/         Streamlit fallback and demonstration interface
    configs/     Versioned model, state, and operating-policy contracts
    docs/        Architecture, security, deployment, and operating guides
    frontend/    Next.js and React dashboard
    models/      Local checkpoint artifacts (Git ignored)
    scripts/     Reproducibility and validation commands
    src/agent/   Remote Sentinel Sensor CLI and delivery runtime
    src/api/     Central FastAPI service and contracts
    src/sensors/ Sensor registry and isolated remote runtimes
    tests/       Automated regression, API, runtime, and security tests

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Distributed Sensor Architecture](docs/DISTRIBUTED_SENSOR_ARCHITECTURE.md)
- [Remote Telemetry](docs/REMOTE_TELEMETRY.md)
- [Remote Telemetry Contract](docs/REMOTE_TELEMETRY_CONTRACT.md)
- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md)
- [Sensor Operations](docs/SENSOR_OPERATIONS.md)
- [Security Boundaries](docs/SECURITY.md)
- [Current Limitations](docs/LIMITATIONS.md)
- [Contributing](CONTRIBUTING.md)

## Limitations and roadmap

Sentinel is currently a single-node, process-local platform. Its capture path
depends on host access, supported interfaces, and Scapy/Npcap/libpcap. It has
not made production-capacity, long-duration soak, penetration-test, HA, or
automatic-response claims. PCAP fusion remains excluded from the frozen V1
flow artifact because authoritative matching provenance is unavailable.

The next engineering steps are a real multi-host sensor soak, TLS reverse
proxy deployment validation, service-manager packaging for the agent,
certificate-based identity, and broader source-capable telemetry adapters.

## License

Project-owned code is released under the [MIT License](LICENSE). Dataset, PCAP,
and model-artifact terms are separate; contributors must have the right to
share anything they submit.

---

<div align="center">
  <sub>Sentinel / NI · Forecast first. Respond deliberately.</sub>
</div>
