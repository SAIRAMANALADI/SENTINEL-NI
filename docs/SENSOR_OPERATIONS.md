# Sensor Operations

```powershell
python -m src.agent status
python -m src.agent config
python -m src.agent stop
python -m src.agent start
```

Use a host service manager to supervise the agent in production. The local
buffer is bounded and sequence ordered. For a `DEGRADED` sensor, check
connectivity, capture permission, interface name, and buffered batch count. A
full buffer is a delivery failure and must not be treated as successful
collection.

Operators with viewer credentials can use `GET /api/v1/sensors`,
`GET /api/v1/sensors/{sensor_id}`, `/api/v1/health`, and `/api/v1/ready`. A
sensor credential can use only its own `GET /api/v1/sensors/{sensor_id}/status`
and heartbeat operation; it cannot list sensors or use administrative APIs.
The dashboard Connected servers view reports REGISTERED, ONLINE, DEGRADED, or
OFFLINE based on actual freshness; registration alone is never ONLINE. It does
not claim central capture of remote packets.

Telemetry is delivered as bounded version-1 batches. `sent_at` records
delivery time; state timestamps remain the ten-second network timeline. The
agent retries network, timeout, rate-limit, and temporary-server failures with
bounded backoff and retains them in the bounded disk buffer. Authentication,
schema, timestamp, or sequence failures require operator action.

## Reliability status

`python -m src.agent status` reports the redacted server URL, sensor identity,
agent/capture/telemetry status, state and delivery timestamps, buffer count and
bytes, overflow counters, sequence progress, and the latest safe error. It
never prints runtime tokens. `DROP_OLDEST` is visible in the buffer status and
means the oldest unsent envelope was intentionally sacrificed at capacity;
inspect capacity and connectivity before treating a run as lossless.

The central sensor status separates Agent, Telemetry, and Forecast. A fresh
heartbeat with stale telemetry is `DEGRADED`; no fresh heartbeat is `OFFLINE`.
`WAITING` forecast health means the sensor has not yet supplied ten contiguous
valid states. See `SENSOR_RELIABILITY.md` for recovery and restart semantics.
