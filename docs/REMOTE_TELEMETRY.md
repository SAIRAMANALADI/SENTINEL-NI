# Remote Telemetry Contract

Endpoint: `POST /api/v1/telemetry`
Header: `X-Sentinel-Sensor-Token: <runtime-token>`

Payload shape:

```json
{
  "schema_version": "1",
  "sensor_id": "sensor-0123456789abcdef",
  "sequence": 1,
  "sent_at": "2026-09-02T12:00:00Z",
  "states": [{
    "timestamp": "2018-02-22T01:00:00Z",
    "capture_day": "2018-02-22",
    "features": {"<all 17 schema features>": 0.0}
  }]
}
```

The placeholder feature map is documentation notation, not a valid payload.
Use every exact feature name from `configs/state_feature_schema.yaml`. Batches
are limited to 60 states, must stay within one capture day, and must use
contiguous ten-second timestamps. Duplicate accepted batches are acknowledged
without re-running inference. Malformed, non-finite, oversized,
unauthenticated, out-of-order, or cross-day data is rejected.
