# Remote Telemetry Implementation Report — Phase C

**Status:** Phase C complete for the authenticated state-telemetry path. The
frozen forecasting and data contracts were not changed.

## 1. Telemetry architecture

The monitored server observes its own interface out-of-band:

```text
remote packets
  -> LiveTelemetryAdapter (metadata only)
  -> AgentCollector
  -> existing FlowBuilder
  -> existing aggregate_flow_window (10-second state)
  -> bounded agent queue/batcher
  -> authenticated POST /api/v1/telemetry
  -> RemoteSensorRuntimeStore[sensor_id]
  -> existing L=10 state buffer
  -> existing LSTM K=5 inference
  -> API/dashboard sensor view
```

Customer application requests continue directly to the application server.
Sentinel is not a reverse proxy and does not sit in the request path.

## 2. Telemetry contract

The version-1 envelope is defined in
[`REMOTE_TELEMETRY_CONTRACT.md`](REMOTE_TELEMETRY_CONTRACT.md). It carries a
registered sensor ID, positive sequence, timezone-aware delivery timestamp,
and 1–60 state records. Each state uses the existing exact 17-feature
network-state schema plus its state timestamp and capture day.

## 3. Agent transport

`src/agent/transport.py` uses standard-library HTTPS-capable URL transport with
timeouts. `src/agent/client.py` applies the sensor runtime token only to
sensor heartbeat, status, and telemetry operations. Production configuration
rejects plaintext HTTP; development permits local HTTP for testing.

## 4. Authentication

Registration consumes a short-lived, one-time enrollment credential. The
central registry stores only a hash of the runtime token. The telemetry
dependency authenticates the body sensor ID and header token together, so a
credential cannot select another sensor. Sensor credentials cannot enumerate
sensors or call admin/operator endpoints.

## 5. Batching

`src/agent/telemetry.py` provides `TelemetryBatcher`. It assigns one sensor ID,
monotonic sequence, schema version, and UTC send timestamp to bounded
envelopes without changing state values. Defaults are six states per batch and
a five-second partial-batch wait; the central request maximum is 60 states.

## 6. Retry

Connection failures, timeouts, 408, 425, 429, and 5xx responses are treated as
transient. Retry delay is exponential, starts at the configured one-second
base, and is capped at 60 seconds. 401, 403, 422, and other permanent
responses are surfaced and are not retried indefinitely.

## 7. Buffering

`DiskTelemetryBuffer` writes batches atomically under sequence-named files and
delivers them in sequence order. It is capped at 256 batches/64 MiB by
default. A full buffer raises an explicit delivery error; the agent does not
claim that an unsent batch was delivered. This is local disk durability, not a
distributed queue.

## 8. Sequence handling

Sequence advancement is persisted when an envelope is created, before send.
The central registry records the last accepted sequence and envelope hash.
Identical retransmission receives `DUPLICATE_ACKNOWLEDGED` without re-running
inference. Older or conflicting sequences are rejected. Delivery is bounded
at-least-once with deduplication, not exactly-once.

## 9. Runtime integration

`POST /api/v1/telemetry` validates the batch and calls the existing
`RemoteSensorRuntimeStore.ingest(sensor_id, states)`. Each remote runtime owns
its own StateBuffer, history, counters, latest forecast, and errors. No second
forecaster or model implementation was added.

## 10. Multi-sensor isolation

The sensor ID scopes authentication, sequence ledger, runtime history, L=10
context, forecast, and health. Existing two-sensor tests verify that one
sensor's state history does not contribute to another sensor's forecast.
`sensor_id` is routing metadata and is never sent as a model feature.

## 11. Health integration

Heartbeat and telemetry remain separate. A newly registered sensor is
`REGISTERED`; `ONLINE` requires both fresh heartbeat and telemetry;
`DEGRADED` indicates partial freshness; `OFFLINE` indicates expired heartbeat
freshness. The agent status command reports local buffer state plus the
authenticated central sensor status when available.

## 12. Frontend changes

The existing `SensorFleet` and `CommandCenter` integration is retained. The
selected sensor explicitly scopes the displayed runtime, state count,
freshness, forecast readiness, and five Forecast Scores. No demo, mock, or
local runtime values are presented as remote sensor data. Remote aggregate
telemetry continues to report source attribution as unavailable.

## 13. Security controls

- strict Pydantic schema and extra-field rejection;
- finite numeric feature validation;
- timezone-aware timestamp, date, and ten-second cadence checks;
- request-size and per-sensor rate limits;
- sensor credential and body-identity binding;
- duplicate/conflicting sequence protection;
- bounded atomic disk buffering;
- secret-safe structured logging and hashed central credentials;
- no raw packet payload forwarding;
- no automatic blocking or inline traffic handling.

## 14. End-to-end test result

`tests/api/test_remote_agent_e2e.py::test_real_agent_posts_to_central_and_reaches_lstm`
starts a real Uvicorn central API, registers a sensor through the API, uses a
real `SensorAgent` and `SensorClient`, posts ten valid states through
`POST /api/v1/telemetry`, and verifies that the central runtime reaches
`FORECAST_READY` with real K=5 forecast output. It passed.

## 15. Two-sensor test result

`tests/api/test_remote_sensors.py::test_two_remote_sensors_keep_forecast_histories_isolated`
passed. It verifies separate state counts and forecast readiness for two
registered sensors using the central telemetry endpoint. No cross-sensor
state mixing was observed.

## 16. Full regression result

```text
python -m pytest -q
237 passed, 2 warnings in 71.88s
```

Focused Phase C/control-plane set:

```text
python -m pytest -q tests/test_sensor_agent.py tests/api/test_remote_sensors.py tests/api/test_remote_agent_e2e.py tests/test_sensor_control_plane.py
22 passed, 2 warnings in 9.76s
```

Additional checks:

```text
frontend: npm run typecheck    passed
frontend: npm run build        passed
docker compose config --quiet  passed
git diff --check               passed
```

Docker runtime validation was not available in this environment:
`docker info` could access the Docker CLI but not the Docker Desktop Linux
engine (`dockerDesktopLinuxEngine` pipe was unavailable). Compose containers
were not started and no runtime-pass claim is made.

## 17. Known limitations

- The central runtime and JSON registry are process-local; they are not HA or
  multi-worker storage.
- The agent has no service-manager package or multi-host soak evidence here.
- Production TLS is enforced at the agent URL boundary, but mTLS,
  certificate rotation, OIDC, and a full identity provider are not
  implemented.
- Remote state-only telemetry cannot identify candidate source IPs or support
  source-based mitigation; those values are not fabricated.
- Docker central runtime validation remains pending until the Docker daemon is
  available. The central Compose service does not claim host packet capture.
- The bounded local disk buffer is not a distributed durable queue and does
  not provide exactly-once delivery.

## 18. Exact command to run central Sentinel

Development central service:

```powershell
$env:SIH_TELEMETRY_MODE = "mock"
python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000
```

For deployment, place the API behind a TLS reverse proxy/private network and
configure `SIH_AUTH_ENABLED=true` with role tokens from a secret manager.

## 19. Exact commands to register an agent

On the central operator side, create a short-lived enrollment credential with
the admin bearer token:

```powershell
$headers = @{ Authorization = "Bearer $env:SIH_ADMIN_TOKEN" }
$body = @{ expires_in_seconds = 600 } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://central-host:8000/api/v1/sensors/enrollment -Headers $headers -Body $body -ContentType application/json
```

On the monitored server:

```powershell
python -m src.agent init --server-url https://central-host --interface "Ethernet" --environment production
python -m src.agent register --enrollment-token <one-time-token>
```

The enrollment token is consumed once. Never place the admin token in the
agent configuration or browser bundle.

## 20. Exact command to start an agent

```powershell
python -m src.agent start
```

The agent must run directly on the monitored host with the required
Npcap/libpcap capture permission. It does not run customer traffic through
Sentinel.

## 21. Exact command to inspect an agent

```powershell
python -m src.agent status
```

This reports redacted local configuration, buffered batches, and the central
sensor-scoped status when the central API is reachable.

## 22. Exact next phase

Stop Phase C here. The next approved work is deployment validation: Docker
runtime when the daemon is available, service-manager packaging, TLS reverse
proxy verification, and a real multi-host agent soak. Do not begin advanced
source identity, automatic response, mTLS infrastructure, OIDC, HA, or a new
model in this phase.
