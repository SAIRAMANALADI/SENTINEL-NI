# Distributed Sensor Architecture — Phase A–C Contract

**Phase:** A architecture audit plus the implemented Phase B/C control-plane
and telemetry path
**Scope of this document:** the implemented repository as inspected on
2026-09-02. The frozen model, feature schema, local capture semantics, replay,
and frontend forecast behavior remain unchanged.

## 1. Architecture decision

Sentinel is an **out-of-band observability and forecasting system**. A customer's ordinary application requests do not transit Sentinel, are not proxied through Sentinel, and must not be delayed by Sentinel.

```text
Customer traffic
client --------------------------------------------> customer application server

Sentinel telemetry path
remote server interface -> Sentinel Agent -> authenticated HTTPS state telemetry
                                              -> central Sentinel API
                                              -> isolated per-sensor runtime
                                              -> existing LSTM K=5
                                              -> operator dashboard
```

The repository already contains the first distributed-sensor implementation. The purpose of later phases is to harden and operationally validate that implementation, not to create a second competing telemetry path.

## 2. Current architecture

### 2.1 Local capture path

The current local live path is owned by one `LiveRuntimeStore` and is separate from remote sensor runtimes:

```text
Scapy/Npcap/libpcap packet metadata
  -> src.telemetry.live.LiveTelemetryAdapter
  -> src.api.app.Runtime._on_live_event
  -> src.api.live_runtime.LiveRuntimeStore.ingest_event
       -> FlowBuilder (completed bidirectional flows)
       -> SourceActivityAccumulator (source activity only)
       -> build_network_state_for_inference (10-second states)
       -> StateBuffer (L=10, one capture day, no gaps)
       -> predict_network_state_sequence (frozen LSTM, K=5)
       -> source prioritization + recommendation-only mitigation
  -> GET /api/v1/live
  -> frontend CommandCenter / ForecastView / SourceIntelligence
```

`LiveTelemetryAdapter` emits metadata only: timestamp, addresses, ports, protocol, length, TCP flags, and a small set of header-derived fields. It never retains packet objects or payload bytes. `FlowBuilder` creates bounded bidirectional flows and only emits a flow on FIN, RST, timeout, or explicit flush.

The local source path is deliberately distinct from the model path. `SourceActivityAccumulator` produces measured source activity; `src.streaming.source_forecast` ranks those candidate sources beside the network forecast; `src.evaluation.mitigation_policy` returns recommendations only and never blocks traffic.

### 2.2 Replay and mock paths

`src.telemetry.mock.MockTelemetryAdapter` and `src.telemetry.replay.ReplayTelemetryAdapter` remain local API modes selected by `SIH_TELEMETRY_MODE`. They feed the established runtime/replay contracts and must remain independent of remote sensor state. The demo endpoint is deterministic prepared data, not a remote-sensor substitute.

### 2.3 Implemented remote sensor path

```text
remote monitored host
  interface
  -> LiveTelemetryAdapter (metadata only)
  -> src.agent.collector.AgentCollector
  -> FlowBuilder
  -> aggregate_flow_window
  -> exact 10-second state: 17 features + timestamp + capture_day
  -> SensorAgent batching / bounded disk buffer
  -> POST /api/v1/telemetry over HTTPS

central Sentinel
  -> request-size, Pydantic, identity, date, cadence, sequence, duplicate, and rate checks
  -> RemoteSensorRuntimeStore[sensor_id]
  -> RemoteSensorRuntime[sensor_id]
  -> StateBuffer (L=10, isolated per sensor)
  -> existing predict_network_state_sequence()
  -> GET /api/v1/sensors and GET /api/v1/sensors/{sensor_id}
  -> frontend SensorFleet selection and reused forecast presentation
```

The remote agent therefore connects **after state construction**, not to the customer's application traffic path and not to the central `LiveRuntimeStore`. Central ingestion enters at `POST /api/v1/telemetry`, then calls `RemoteSensorRuntimeStore.ingest(sensor_id, states)`.

## 3. Frozen forecasting contract

Both local and remote state paths must preserve the existing contract:

- exact 17 ordered numeric features from `configs/state_feature_schema.yaml` (`network-state-v1.0`);
- state cadence exactly 10 seconds;
- exactly 10 contiguous, same-day states per LSTM input;
- existing checkpoint and preprocessing artifacts;
- existing direct multi-output LSTM K=5 forecast semantics: +10, +20, +30, +40, and +50 seconds;
- approved balanced operating threshold `0.19` and the display term **Forecast Score**;
- existing future-target definition in `docs/TARGET_STATE_SPEC.md`; target columns are not remote telemetry inputs.

`sensor_id` is routing and ownership metadata. It must not be added to the 17 feature columns, sent to the model, used as a model feature, or used to alter the operating threshold.

## 4. Sensor identity, registration, and authentication boundaries

### Identity

`src.sensors.registry.SensorRegistry` creates a persistent central identity shaped as `sensor-<16 hexadecimal characters>`. It stores hostname, agent version, freshness/sequence metadata, and only a SHA-256 hash of the sensor runtime credential.

### Registration flow

```text
administrator bearer token
  -> POST /api/v1/sensors/enrollment
  -> expiring, one-time enrollment credential

remote agent
  -> POST /api/v1/sensors/register
  -> sensor_id + one-time-returned runtime token
  -> src.agent.config.AgentConfig local configuration
```

Enrollment authority, `sensor_id`, and the sensor runtime token are deliberately different values. The agent uses the runtime token only in `X-Sentinel-Sensor-Token`; administrator, operator, and viewer actions use the existing bearer-token role mechanism in `src.api.auth`.

### Authentication boundary

- `src.api.auth.require_role()` controls viewer/operator/admin access to central operator endpoints.
- `src.api.sensors.require_sensor()` and `require_telemetry_sensor()` authenticate sensor runtime credentials independently of user roles.
- The telemetry body `sensor_id` must match the identity authenticated by the header. A sensor cannot choose another sensor's runtime by changing the body.
- The agent transport uses the standard TLS-validating Python URL client when configured with `https://`; it currently also permits `http://` in configuration for local development.

## 5. Telemetry, buffering, and heartbeat boundary

### Telemetry contract

`RemoteTelemetryBatch` version `1` accepts one to sixty states. Every state contains only:

- timestamp;
- capture day;
- a map of exactly the 17 finite model features.

The API rejects extra fields, non-finite values, invalid dates, cross-day batches, non-contiguous ten-second intervals, sensor-ID mismatches, oversized requests, out-of-order sequences, and conflicting duplicate sequences. An identical accepted `sequence` plus payload hash receives a duplicate acknowledgement and does not run inference again.

### Buffering flow

`src.agent.buffer.DiskTelemetryBuffer` writes an unsent batch atomically as a sequence-named JSON file. It delivers batches in sequence order, caps both file count and bytes, and raises an explicit `BufferFullError` instead of silently dropping telemetry. `SensorAgent` retries transient HTTP/network failures with bounded exponential backoff. It does not claim a rejected or full-buffer batch was delivered.

### Heartbeat flow

The agent sends an independent heartbeat containing buffered-batch count and agent version to `POST /api/v1/sensors/{sensor_id}/heartbeat`. Registry health is:

- `ONLINE`: heartbeat and telemetry are fresh;
- `DEGRADED`: the sensor was recently seen but one freshness condition is stale;
- `OFFLINE`: `last_seen` exceeds the heartbeat timeout.

## 6. Multi-sensor isolation

Isolation is already implemented at the following boundaries:

| Boundary | Implementation | Required invariant |
| --- | --- | --- |
| Credential | per-sensor runtime-token hash in `SensorRegistry` | one sensor cannot authenticate as another |
| Delivery ordering | `last_sequence` and batch hash per sensor | one sensor cannot replay/overwrite another's batch history |
| Runtime state | `RemoteSensorRuntimeStore` dictionary keyed by `sensor_id` | each sensor has its own `StateBuffer`, history, forecast, counters, and errors |
| Temporal history | `StateBuffer` per runtime | no cross-sensor or cross-day L=10 sequence |
| UI selection | `selectedSensorId` in `frontend/components/CommandCenter.tsx` | displayed remote forecast is scoped to the selected sensor |
| Local runtime | `LiveRuntimeStore` is not stored in the remote runtime map | remote telemetry cannot overwrite local capture/replay state |

Remote state-only telemetry intentionally has no source IP, flow identity, packet events, or raw packet payload. Consequently `RemoteSensorRuntime.snapshot()` returns an empty source-priority list and `UNAVAILABLE_FROM_AGGREGATED_STATE_TELEMETRY`. Remote mitigation is not fabricated; the local candidate-source and recommendation path remains available only when source-capable local events are present.

## 7. Local versus remote operation

| Mode | Packet capture location | Central input | Forecast state owner | Source attribution |
| --- | --- | --- | --- | --- |
| `mock` | none | prepared mock contract | local runtime | demo/local contract only |
| `replay` | none | approved replay event/state source | local runtime | replay-supported data only |
| local `live` | the central host's selected interface | packet metadata | `LiveRuntimeStore` | measured local source activity; candidate ranking only |
| remote sensor | remote server's selected interface | aggregated 10-second state batches | `RemoteSensorRuntime[sensor_id]` | unavailable from the approved state-only contract |

No mode may send customer application requests through Sentinel. The remote agent observes its local interface and sends telemetry outward; it is not a reverse proxy, traffic broker, inline blocker, or network gateway.

## 8. Frontend implications and reusable components

The Next frontend already has the primitives needed for later operational hardening:

| Requirement | Existing component/module | Current behavior |
| --- | --- | --- |
| Sensors / Add or Connect Server | `frontend/components/SensorFleet.tsx` | presents the administrator-controlled connection workflow and agent commands; it does not call the enrollment endpoint |
| Sensor Health | `SensorFleet.tsx` | displays ONLINE/DEGRADED/OFFLINE, freshness, buffered batches, states, and history |
| Sensor Detail | `SensorFleet.tsx` selected card | displays selected scope, forecast readiness, sequence, and state-only source limitation |
| Sensor Selection | `CommandCenter.tsx` + `SensorFleet.tsx` | `selectedSensorId` scopes the forecast context rendered below |
| Forecast display | `ForecastView.tsx` | can reuse the existing K=5 score/timeline/explanation presentation |
| Candidate sources and mitigation | `SourceIntelligence.tsx` | reuse only when the selected data source actually has source-capable evidence |

The dashboard must continue to state that a remote server is agent-side capture and that state-only telemetry cannot identify candidate sources. It must not present empty remote source lists as evidence of benign traffic.

## 9. Docker and host-capture boundary

`docker-compose.yml` intentionally runs the backend in `SIH_TELEMETRY_MODE=mock`, drops all Linux capabilities, and does not grant host networking, `privileged`, device mappings, or capture capabilities. Docker Compose therefore supports the central API/dashboard path, **not arbitrary host packet capture inside the backend container**.

`docs/LIVE_CAPTURE_IMPLEMENTATION.md` confirms that Scapy/Npcap/libpcap capture is host-level only. A remote agent must run directly on the monitored server with the required capture provider, exact interface, and least capture permission. Do not weaken the central Compose security profile just to capture packets.

## 10. Architectural conflicts and operational risks

These are evidence-backed current limitations, not work performed in Phase A:

1. **Remote runtimes are process-local and in memory.** `RemoteSensorRuntimeStore` and its L=10 histories/forecasts are not durable. A central restart requires every sensor to rebuild a ten-state history; multi-worker/horizontally scaled API processes cannot safely share this in-memory runtime.
2. **The current registry is single-process only.** Its `RLock` protects one process, not multiple API processes sharing the JSON file. It is not an HA or multi-instance registry. Compose now provides a named volume for registry persistence, but that does not provide distributed locking or HA.
3. **The agent configuration permits plaintext HTTP only in development.** Production validation fails closed unless the server URL is `https://`. Development HTTP is intentionally local-only and must not be used for deployment.
4. **Telemetry delivery is bounded at-least-once, not exactly-once.** Sequence/hash deduplication prevents duplicate inference for accepted retransmissions, but a process or network failure around acknowledgement can still require retransmission and operator-visible recovery.
5. **The browser is not the enrollment authority.** Phase B removes the dashboard call to the admin-only enrollment endpoint. An administrator must create the one-time credential through the server-side control-plane path, then provide only that one-time credential to the remote operator. The Next dashboard now has a server-side role-token session adapter when enabled; it is not OIDC/SSO, is process-local, and still requires external deployment validation.
6. **Remote source attribution is intentionally unavailable.** The approved remote state contract excludes source identity. Adding source attribution requires a separately reviewed privacy, identity, and schema contract; it must not be inferred from aggregate features.
7. **The agent is not service-manager packaged and lacks a real multi-host soak.** Its CLI and bounded buffer are implemented, but service supervision, TLS reverse-proxy validation, certificate lifecycle, and multi-host Scapy/Npcap operational evidence remain open.
8. **Capture documentation reconciliation completed.** The current `LiveRuntimeStore` and remote `AgentCollector` both implement packet-metadata-to-flow-to-state conversion. Older wording that described this path as not yet connected to inference is historical and should not be used as the current capability statement. This does not change the frozen contract or add raw-payload retention.

## 11. Exact implementation surface for later phases

### Existing files that may be changed in later hardening phases

| Later concern | Files/modules to change | Why |
| --- | --- | --- |
| durable central registry and restart behavior | `docker-compose.yml`, `src/platform/config.py`, `src/sensors/registry.py`, `src/sensors/runtime.py`, deployment docs | preserve registration state safely and define restart/history behavior |
| secure control-plane authentication | `src/api/auth.py`, `src/api/sensors.py`, `src/api/app.py`, `src/api/models.py`, `frontend/lib/api.ts`, `frontend/components/SensorFleet.tsx` | avoid browser-exposed role tokens and resolve agent status authorization |
| TLS/mTLS and credential lifecycle | `src/agent/transport.py`, `src/agent/config.py`, `src/agent/client.py`, `src/sensors/registry.py`, `docs/SENSOR_SECURITY.md` | enforce production transport and certificate/rotation policy |
| agent service and operational controls | `src/agent/cli.py`, `src/agent/client.py`, `src/agent/config.py`, `src/agent/buffer.py`, `docs/SENSOR_INSTALLATION.md`, `docs/SENSOR_OPERATIONS.md` | supervisor packaging, recovery, buffer observability, and safe status behavior |
| sensor telemetry observability | `src/platform/metrics.py`, `src/platform/audit.py`, `src/api/app.py`, `src/sensors/runtime.py`, frontend sensor components | add sensor-scoped metrics/audit without exposing raw telemetry |
| remote-source capability, only after a new approved contract | new privacy/schema/design documentation plus `src/api/models.py`, agent collector/contract modules, source modules, frontend | do not reuse aggregate state data to invent source attribution |

### Files/modules that must remain untouched by distributed-sensor phases

- `models/lstm_multistep_k5.pt` and `models/baseline_preprocessor.joblib`;
- `src/models/lstm_world_model.py` and the model architecture/checkpoint contract;
- `src/forecasting/inference.py` except for non-semantic integration validation; no model, score, horizon, or threshold change;
- `configs/state_feature_schema.yaml` and its 17 feature definitions;
- `docs/TARGET_STATE_SPEC.md`, the target definition, and approved label semantics;
- `configs/operating_policy.yaml`, including the balanced `0.19` threshold;
- `src/features/` aggregation semantics unless a separately approved data-contract version is created;
- local `mock`, `replay`, and existing local capture behavior in `src/telemetry/`, `src/api/live_runtime.py`, and their regression contracts;
        - `src/streaming/source_activity.py`, `src/streaming/source_forecast.py`, and `src/evaluation/mitigation_policy.py` semantics: no automatic blocking and no unsupported remote attribution.

## 12. Phase D reliability boundary

Phase D hardening is limited to the agent delivery and sensor-status layers.
`DiskTelemetryBuffer` is bounded, atomic, and restart-safe for local queued
envelopes. Overflow is explicit (`DROP_OLDEST` or `REJECT_NEW`), corrupt and
partial files are quarantined, and permanent API rejection is not retried
forever. `SensorAgent` keeps collection running across transient transport and
heartbeat failures and flushes in sequence after reconnect.

Heartbeat metadata is independent from accepted telemetry. Central lifecycle
evaluation uses heartbeat freshness for `OFFLINE`, and requires both fresh
heartbeat and fresh telemetry for `ONLINE`; otherwise a communicating sensor
is `DEGRADED`. The API and SensorFleet UI expose the three separate health
planes: Agent, Telemetry, and Forecast.

The detailed policy and known limitations are in
[`SENSOR_RELIABILITY.md`](SENSOR_RELIABILITY.md) and the measured implementation
record is in
[`SENSOR_RELIABILITY_IMPLEMENTATION_REPORT.md`](SENSOR_RELIABILITY_IMPLEMENTATION_REPORT.md).

## 13. Regression-sensitive tests

Later phases must preserve and extend—not weaken—the following evidence:

| Behavior | Existing tests |
| --- | --- |
| remote enrollment, token checks, cadence, deduplication, rate limits, real inference, and two-sensor separation | `tests/api/test_remote_sensors.py` |
| agent disk-buffer ordering, token redaction, and no raw-packet retention claim | `tests/test_sensor_agent.py` |
| local L=10 buffering, rolling forecasts, stale state, out-of-order handling, and inference concurrency | `tests/test_live_runtime_store.py` |
| local session restart isolation for history, source priorities, and mitigation | `tests/test_live_restart_isolation.py` |
| metadata-only packet conversion, capture backend status, bounded queue, and failures | `tests/test_live_telemetry.py`, `tests/test_live_telemetry_contract.py`, `tests/test_live_telemetry_failures.py` |
| bidirectional flow accounting, closure, timeout, ordering, and bounds | `tests/test_flow_builder.py` |
| exact state schema, interval, finite-value, day-boundary, and L=10 rules | `tests/test_network_state.py`, `tests/test_state_buffer.py`, `tests/test_live_inference_state.py` |
| frozen inference/schema/policy/target behavior | `tests/test_inference.py`, `tests/test_input_validation.py`, `tests/test_policy_integration.py`, `tests/test_k1_consistency.py` |
| local API/dashboard contract and source/mitigation safety | `tests/api/test_api_contracts.py`, `tests/test_live_api.py`, `tests/test_live_dashboard_contract.py`, `tests/test_source_prioritization.py`, `tests/test_mitigation_policy.py` |

## 14. Recommended implementation order after Phase A

1. **Phase B — control-plane hardening:** choose a durable registry strategy, secure the dashboard administrative enrollment flow, and resolve the authenticated agent-status mismatch. Add focused regression tests first.
2. **Phase C — central ingestion resilience:** make runtime/registry restart behavior explicit, add sensor-scoped audit/metrics, and define safe multi-process limitations or a supported shared-state design.
3. **Phase D — agent operational hardening:** enforce production HTTPS, define certificate/credential rotation, package supervision guidance, and test retry/restart behavior without changing telemetry semantics.
4. **Phase E — deployment validation:** validate TLS reverse proxy, registry persistence across Compose recreation, and a real two-host capture/telemetry soak using supported interfaces.
5. **Phase F — optional remote source enrichment research:** begin only after a separate approved source-identity/privacy contract. It must not alter the frozen 17-feature LSTM input or fabricate candidate sources.

## 15. Phase A conclusion

The correct remote integration point already exists: host-local agent aggregation followed by authenticated state ingestion into an isolated `RemoteSensorRuntimeStore`. The system supports sensor registration, heartbeat, buffering, per-sensor sequences, and forecast isolation while preserving local, replay, and mock behavior. Production readiness is blocked only by the operational/control-plane limitations listed above; no data-pipeline or ML redesign is required for Phase A.
