# API Reference — Sensor Fleet

All endpoints use the existing v1 API authentication boundaries. Viewer role
credentials read fleet/detail/forecast data. Sensor runtime credentials use
`X-Sentinel-Sensor-Token` and are limited to their own status, heartbeat, and
telemetry. Operator role is required to disable a sensor. Secrets never appear
in responses.

## Fleet

`GET /api/v1/sensors`

Returns compact sensor summaries and measured fleet health counts. It does not
include state histories, forecast explanations, or raw telemetry.

`GET /api/v1/sensors/{sensor_id}`

Returns one sensor's identity, lifecycle/freshness, buffer/sequence metadata,
three-plane health, and its own runtime snapshot. Unknown IDs return `404`.

`GET /api/v1/sensors/{sensor_id}/forecast`

Returns the current computed K=5 forecast for that sensor. Before ten valid
states, it returns HTTP 200 with `forecast_ready=false`, a pending status, and
no forecast object. It never recomputes inference on GET.

`GET /api/v1/sensors/{sensor_id}/status`

Sensor-credential-scoped status endpoint. A sensor credential cannot read a
different sensor or enumerate the fleet.

## Lifecycle

`POST /api/v1/sensors/{sensor_id}/disable`

Operator-only, non-destructive offboarding. The registry record remains for
audit, is marked `DISABLED`, is presented as `OFFLINE`, and future calls using
the old sensor runtime credential receive `401`.

`POST /api/v1/sensors/{sensor_id}/rotate-credential`

Admin-only credential rotation. The response contains a new runtime credential
once for secure out-of-band delivery; the old credential is immediately
invalid, while the same sensor ID, runtime history, and health record remain.
Disabled sensors cannot be rotated. The frontend never calls this endpoint.

## Existing telemetry path

`POST /api/v1/telemetry` accepts authenticated version-1 batches containing the
exact 17 finite state features plus timestamp/capture day. The body sensor ID
must match the authenticated credential. Sequence ordering, duplicate hashes,
rate limits, same-day cadence, and runtime routing remain per sensor.

`POST /api/v1/sensors/{sensor_id}/heartbeat` records safe agent metadata,
including capture status, buffered count/bytes, state timestamp, and sequence
progress. Heartbeat receipt does not make telemetry fresh by itself.

## Request and transport limits

The API rejects bodies over `SIH_MAX_REQUEST_BYTES` (default 2,000,000 bytes),
remote batches over 60 states, non-finite feature values, cross-day or
non-contiguous states, and sensor telemetry/heartbeat over the configured
per-sensor sliding limit (default 60 requests/minute). Registration uses a
separate process-local source limit (default 10/minute), plus the short-lived
one-time enrollment credential. Limits are not shared across multiple API
workers or hosts in this release.
