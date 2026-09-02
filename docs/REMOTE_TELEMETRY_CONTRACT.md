# Remote Telemetry Contract v1

Sentinel telemetry is out-of-band. Customer application requests continue
directly to the customer application server; they never pass through Sentinel.
The remote agent sends completed, aggregate network states to the central API.

## Endpoint and authentication

```text
POST /api/v1/telemetry
Content-Type: application/json
X-Sentinel-Sensor-Token: <sensor runtime token>
```

The runtime token is issued once during registration and is stored only as a
hash in the central registry. It is scoped to the sensor named in the payload.
It cannot list sensors or call operator/admin APIs.

## Envelope

```json
{
  "schema_version": "1",
  "sensor_id": "sensor-0123456789abcdef",
  "sequence": 123,
  "sent_at": "2026-09-02T12:00:00+00:00",
  "states": [
    {
      "timestamp": "2026-09-02T12:00:00+00:00",
      "capture_day": "2026-09-02",
      "features": {
        "flow_count": 0.0,
        "byte_sum": 0.0,
        "packet_sum": 0.0,
        "mean_duration": 0.0,
        "median_duration": 0.0,
        "mean_iat": 0.0,
        "iat_std": 0.0,
        "syn_flow_ratio": 0.0,
        "ack_flow_ratio": 0.0,
        "rst_flow_ratio": 0.0,
        "fwd_byte_share": 0.0,
        "fwd_packet_share": 0.0,
        "unique_destination_port_count": 0.0,
        "bytes_per_second": 0.0,
        "packets_per_second": 0.0,
        "packet_size_mean": 0.0,
        "packet_size_std": 0.0
      }
    }
  ]
}
```

The feature names and ordering are authoritative in
[`configs/state_feature_schema.yaml`](../configs/state_feature_schema.yaml).
The telemetry schema references that contract; it does not redefine the
model. Each state has exactly those 17 finite numeric features plus
`timestamp` and `capture_day`. `sensor_id` is routing metadata and is never a
model feature. Raw packets and payloads are not transmitted.

## Validation rules

- `schema_version` is exactly `"1"`.
- `sensor_id` is the registered `sensor-` identifier and must match the header
  credential.
- `sequence` is a positive integer scoped to that sensor.
- `sent_at` and each state `timestamp` are timezone-aware ISO timestamps.
- `capture_day` must equal the UTC calendar date represented by the state
  timestamp.
- A batch contains 1–60 states, stays within one capture day, and uses
  contiguous ten-second state timestamps.
- The API enforces its configured request-size and per-sensor rate limits.
- Extra fields, missing fields, non-finite numbers, malformed timestamps,
  invalid feature maps, and invalid credentials are rejected.

Delivery time (`sent_at`) is distinct from the network-state timeline
(`timestamp`). Forecast timestamps are derived from the state timeline.

## Sequence and delivery semantics

The agent starts at its persisted next sequence and advances it when an
envelope is created, before network delivery. This prevents a restart from
reusing a sequence that may already be buffered. The central registry stores
the last accepted sequence and a SHA-256 hash of the accepted envelope.

| Condition | Behavior |
| --- | --- |
| New sequence greater than the last accepted | Validate, ingest once, then accept and record it |
| Same sequence and same envelope hash | Return `DUPLICATE_ACKNOWLEDGED`; do not run inference again |
| Same/older sequence with a different envelope | Reject with a sequence conflict |
| 401/403/422 or other permanent validation response | Surface the failure; do not retry forever |
| Network failure, timeout, 408/425/429, or 5xx | Keep the batch in the bounded disk buffer and retry with bounded exponential backoff |
| Buffer reaches its batch/byte limit | Raise an explicit delivery failure; never claim delivery |

This is bounded at-least-once delivery with server-side deduplication. It is
not exactly-once delivery. A gap in state timestamps is not interpolated; the
sensor runtime resets its L=10 history and waits for a new contiguous run.

## Agent defaults

The agent defaults to batches of 6 states, a 5-second maximum wait for a
partial batch, a 20-second heartbeat, a 256-batch/64 MiB disk buffer, and a
1-second retry base capped at 60 seconds. All are configuration values; the
central maximum of 60 states per request remains authoritative.

## Central processing

After validation, the API calls the existing
`RemoteSensorRuntimeStore.ingest(sensor_id, states)`. That runtime owns a
separate L=10 history and the existing K=5 LSTM inference for every sensor.
The system does not create a forecast until ten valid contiguous states for
that sensor and capture day are available. Remote aggregate state telemetry
does not contain source identity, so candidate-source attribution is not
fabricated.
