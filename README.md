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

## Telemetry sources

Sentinel keeps collection separate from forecasting through one bounded
collector contract. The existing Scapy/Npcap/libpcap path, authenticated
Remote Agent path, Replay, and test-only Mock source are available today.
Zeek `conn.log` ingestion is a real partial integration: it validates and
normalizes documented JSON-lines or TSV connection records, but it is not
forecast-compatible by itself because the log lacks required packet-size,
flow-IAT, and TCP flag-count fields. NetFlow and IPFIX are explicit planned
extension points, not enabled listeners.

All sources remain out of band from customer application traffic. Source
identity and capability metadata are operational controls, never model
features. Read [Telemetry Sources](docs/TELEMETRY_SOURCES.md), [Zeek
Integration](docs/ZEEK_INTEGRATION.md), and [Telemetry Source Security](docs/TELEMETRY_SOURCE_SECURITY.md)
before configuring an external collector.

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

For the shortest operator path, start with [Operator Quickstart](docs/OPERATOR_QUICKSTART.md).
For supported platforms and evidence boundaries, see
[Environment Support](docs/ENVIRONMENT_SUPPORT.md). This repository is an
open-source release candidate, not a claim of production capacity or universal
platform support.

### First-time operator path

The primary product journey is **Overview → Sensors → Add Sensor → Sensor
Detail → Forecast → Sources → Mitigation**. Start Central Sentinel, issue a
short-lived enrollment credential as an administrator, install and register
the agent on the monitored server, then wait for fresh heartbeat and
aggregated telemetry. The dashboard keeps Agent, Telemetry, and Forecast
health separate, and it withholds forecast output until ten valid contiguous
states are available. Replay is a secondary walkthrough for prepared data and
is always labeled as demo/replay mode.

Customer requests never pass through Sentinel: the customer application keeps
its normal request/response path while the sensor observes traffic in parallel.

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

    sentinel-agent init --server-url https://sentinel.example --interface "Ethernet" --environment production
    sentinel-agent register --enrollment-token <one-time-enrollment-token>
    sentinel-agent config validate
    sentinel-agent start
    sentinel-agent status

On Linux, install it as a user systemd service after registration:

    sentinel-agent service install
    systemctl --user enable --now sentinel-agent

Windows-native service installation is not included in this release; use an
approved Windows service manager to launch the installed command. The agent
requires only outbound connectivity from the customer server and observes the
application interface in parallel.

The central dashboard reports registration, heartbeat freshness, telemetry
freshness, buffer depth, history readiness, and the sensor-scoped forecast. It
does not report a sensor as online merely because it was registered.

Read the [agent installation guide](docs/AGENT_INSTALLATION.md), the
[agent operations guide](docs/AGENT_OPERATIONS.md), the
[distributed architecture](docs/DISTRIBUTED_SENSOR_ARCHITECTURE.md), and the
[sensor security guide](docs/SENSOR_SECURITY.md) before deployment.

The public release contract is recorded in the [Public Release Manifest](docs/PUBLIC_RELEASE_MANIFEST.md)
(the older [Release Manifest](docs/RELEASE_MANIFEST.md) is retained as a compatibility
pointer), and contributor setup is in [Development Guide](docs/DEVELOPMENT.md).

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
| Sensor operations | GET /api/v1/sensors, GET /api/v1/sensors/{sensor_id}, GET /api/v1/sensors/{sensor_id}/forecast, POST /api/v1/sensors/{sensor_id}/heartbeat, POST /api/v1/sensors/{sensor_id}/disable |
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
proxy, an authenticated Central Sentinel API, and the bundled dashboard
session boundary enabled with `SIH_DASHBOARD_AUTH_ENABLED=true`. Dashboard
login accepts one of the server-side viewer/operator/admin role tokens and
never sends a bearer token to the browser. mTLS, OIDC, tenant isolation, and
high availability are future hardening work; the v0.1 dashboard session store
is process-local and in-memory, so restarts invalidate sessions and multi-
instance deployment requires sticky routing.

## Verification

The current repository verification record includes:

    python -m pytest -q       323 passed, 2 warnings
    npm run typecheck         passed
    npm run build             passed
    python -m build           wheel and sdist passed
    python scripts/release_audit.py  passed
    pip check                 passed
    docker compose config     passed; local Compose runtime health/restart passed

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
    models/      Tracked release checkpoints plus ignored/generated local artifacts
    scripts/     Reproducibility and validation commands
    src/agent/   Remote Sentinel Sensor CLI and delivery runtime
    src/api/     Central FastAPI service and contracts
    src/sensors/ Sensor registry and isolated remote runtimes
    tests/       Automated regression, API, runtime, and security tests

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Distributed Sensor Architecture](docs/DISTRIBUTED_SENSOR_ARCHITECTURE.md)
- [Remote Telemetry](docs/REMOTE_TELEMETRY.md)
- [Telemetry Sources](docs/TELEMETRY_SOURCES.md)
- [Zeek Integration](docs/ZEEK_INTEGRATION.md)
- [NetFlow Integration](docs/NETFLOW_INTEGRATION.md)
- [IPFIX Integration](docs/IPFIX_INTEGRATION.md)
- [Telemetry Source Security](docs/TELEMETRY_SOURCE_SECURITY.md)
- [Remote Telemetry Contract](docs/REMOTE_TELEMETRY_CONTRACT.md)
- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md)
- [Real Deployment Runbook](docs/REAL_DEPLOYMENT_RUNBOOK.md)
- [Deployment Test Matrix](docs/DEPLOYMENT_TEST_MATRIX.md)
- [Staging Validation Report](docs/STAGING_VALIDATION_REPORT.md)
- [Failure Recovery Matrix](docs/FAILURE_RECOVERY_MATRIX.md)
- [Agent Installation](docs/AGENT_INSTALLATION.md)
- [Agent Operations](docs/AGENT_OPERATIONS.md)
- [Agent Upgrades](docs/AGENT_UPGRADES.md)
- [Agent Troubleshooting](docs/AGENT_TROUBLESHOOTING.md)
- [Agent Security](docs/AGENT_SECURITY.md)
- [Sensor Operations](docs/SENSOR_OPERATIONS.md)
- [Security Boundaries](docs/SECURITY.md)
- [Security Architecture](docs/SECURITY_ARCHITECTURE.md)
- [Threat Model](docs/THREAT_MODEL.md)
- [Credential Lifecycle](docs/CREDENTIAL_LIFECYCLE.md)
- [TLS Deployment](docs/TLS_DEPLOYMENT.md)
- [Current Limitations](docs/LIMITATIONS.md)
- [Contributing](CONTRIBUTING.md)
- [Release Notes](docs/RELEASE_NOTES.md)
- [Public Release Manifest](docs/PUBLIC_RELEASE_MANIFEST.md)
- [Final Public Release Checklist](docs/FINAL_PUBLIC_RELEASE_CHECKLIST.md)
- [Phase U Final Public Release Report](docs/PHASE_U_FINAL_PUBLIC_RELEASE_REPORT.md)
- [Public Release Checklist](docs/PUBLIC_RELEASE_CHECKLIST.md)
- [External Validation](docs/EXTERNAL_VALIDATION.md)
- [Issue Triage](docs/ISSUE_TRIAGE.md)
- [Release Artifact Checksums](docs/RELEASE_ARTIFACT_SHA256SUMS.txt)
- [Subagent Release Review](docs/SUBAGENT_RELEASE_REVIEW.md)
- [Phase T Public Release Candidate Report](docs/PHASE_T_PUBLIC_RELEASE_CANDIDATE_REPORT.md)

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
