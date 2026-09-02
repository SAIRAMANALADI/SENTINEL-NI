# Multi-Sensor Architecture — Phase E

Sentinel supports multiple out-of-band agents. Customer application traffic
continues directly to the customer server; it never traverses Sentinel.

```text
server A -> agent A -> authenticated telemetry -> central API -> runtime A
server B -> agent B -> authenticated telemetry -> central API -> runtime B
server C -> agent C -> authenticated telemetry -> central API -> runtime C
                                                       -> dashboard fleet/detail
```

## Registry and runtime separation

`SensorRegistry` is the persistent identity and delivery ledger. It stores the
sensor ID, hostname, credential hash, lifecycle/freshness fields, and accepted
sequence metadata. `RemoteSensorRuntimeStore` is the process-local execution
cache. Every sensor runtime owns its own L=10 `StateBuffer`, latest K=5
forecast, counters, timestamps, and safe errors. Runtime history is not
pretended to survive a central process restart; it rebuilds from new telemetry.

`SensorManager` is the central composition boundary. It creates compact fleet
summaries, full sensor detail, sensor-scoped forecast reads, ingestion routing,
and disable operations without scattering global dictionaries through route
handlers.

## Routing and isolation

`POST /api/v1/telemetry` authenticates the sensor identity, validates the exact
version-1 state contract, and routes only to
`RemoteSensorRuntimeStore[sensor_id]`. Sequences and duplicate hashes are
checked per sensor. A sensor's state history, forecast, health, buffer report,
and errors cannot be used for another sensor.

Runtime memory is bounded to the configured maximum sensor count and 128 recent
rows per sensor; the actual forecast context remains L=10. The central fleet
endpoint returns summaries only and does not include histories or explanations.

## Health and lifecycle

The registry lifecycle remains `REGISTERED`, `ONLINE`, `DEGRADED`, and
`OFFLINE`. `ONLINE` requires fresh heartbeat and accepted telemetry.
`DEGRADED` means heartbeat is fresh while telemetry is absent/stale.
`OFFLINE` means heartbeat is absent/stale. A disabled record remains visible as
`OFFLINE` with `registration_state=DISABLED`, but its runtime credential is no
longer accepted. Agent, Telemetry, and Forecast health are returned separately.

## APIs

- `GET /api/v1/sensors`: compact fleet cards and measured counts.
- `GET /api/v1/sensors/{sensor_id}`: authenticated viewer detail, including
  runtime forecast when it exists.
- `GET /api/v1/sensors/{sensor_id}/forecast`: current computed forecast or an
  explicit pending response; it never runs inference on page refresh.
- `GET /api/v1/sensors/{sensor_id}/status`: sensor credential scoped status.
- `POST /api/v1/sensors/{sensor_id}/disable`: operator disable/revocation;
  registry record is retained and future sensor calls are rejected.

Unknown sensors return 404. Known offline, disabled, or forecast-pending
sensors return 200 with explicit status, rather than being confused with a
missing sensor.

## Dashboard behavior

Overview shows actual total, online, degraded, offline, active Predictive
Warning, and forecast-waiting counts. SensorFleet shows each server's status,
Agent/Telemetry/Forecast health, freshness, buffer and sequence facts, and a
clear selected-sensor context. Remote aggregate state telemetry still has no
source identity, so Candidate Sources and Mitigation Recommendations are not
invented for remote sensors.

## Boundaries

The phase does not introduce HA storage, multi-worker shared runtime state,
mTLS, OIDC, Kafka, Kubernetes, source identity, automatic blocking, or customer
traffic interception. Docker remains a central API/dashboard deployment; host
packet capture stays with the agent on the monitored server.
