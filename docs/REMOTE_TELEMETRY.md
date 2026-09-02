# Remote Telemetry

Sentinel observes a remote server out-of-band. Customer application requests
continue directly to the application server. The agent is not a reverse
proxy, gateway, or inline traffic blocker.

The authoritative payload and delivery contract is documented in
[`REMOTE_TELEMETRY_CONTRACT.md`](REMOTE_TELEMETRY_CONTRACT.md).

Endpoint: `POST /api/v1/telemetry`
Header: `X-Sentinel-Sensor-Token: <runtime-token>`

The remote agent uses the existing host-local metadata capture, flow builder,
and 10-second aggregator. It sends completed states containing timestamp,
capture day, and the exact 17 finite features from
`configs/state_feature_schema.yaml`. It never forwards raw packets or
payloads.

The central API authenticates the sensor identity, validates schema/version,
finite values, timezone-aware timestamps, capture-day consistency, contiguous
ten-second cadence, request size, rate, and sequence. It calls the existing
`RemoteSensorRuntimeStore.ingest(sensor_id, states)`; it does not create a
second forecasting pipeline. Each sensor has an isolated L=10 history and the
existing K=5 inference path. No forecast is returned until ten valid
contiguous states for that sensor and day are available.

The agent uses bounded state memory and a bounded, atomic disk buffer. New
envelopes receive a persisted per-sensor sequence. Network failures, timeouts,
temporary HTTP errors, and rate limits are retried with bounded exponential
backoff; permanent authentication or validation failures are surfaced and are
not retried indefinitely. Accepted duplicate sequence/hash pairs are
acknowledged without running inference twice. Delivery is bounded
at-least-once, not exactly-once.

`sent_at` is delivery time and is distinct from each state's network timeline.
Heartbeat and telemetry freshness remain separate: `REGISTERED` means no
activity yet, `ONLINE` requires both fresh heartbeat and telemetry, `DEGRADED`
means one freshness condition is stale, and `OFFLINE` means heartbeat freshness
has expired.

Remote aggregate state telemetry contains no source identity. Remote
candidate-source attribution and source-based mitigation are therefore not
fabricated; the API exposes that limitation explicitly.
