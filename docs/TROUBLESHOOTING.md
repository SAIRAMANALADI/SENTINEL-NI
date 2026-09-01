# Troubleshooting

## Backend unavailable

Check that the backend process is running and inspect:

```text
GET /api/v1/health
GET /api/v1/ready
```

`health` means the process responds. `ready` also checks configuration,
schema, policy, model, and telemetry availability. In production, missing
authentication configuration intentionally keeps readiness false.

## Live capture unavailable

Run interface discovery, confirm the exact interface name, install Npcap or
libpcap as appropriate, and grant only the required capture permission. The
service reports `LIVE_UNAVAILABLE`, `LIVE_PERMISSION_DENIED`, or `LIVE_ERROR`
with a safe reason.

## Forecast waiting for history

This is expected after startup or restart. The runtime requires ten valid
10-second states. Check `state.buffer_size`, `state.buffer_required`, event
quality, flow closure, and telemetry freshness in `/api/v1/live`.

## DATA STALE

The adapter has not observed a packet within the configured stale interval.
Verify interface visibility and capture permissions. A stale result is not a
current-live result.
