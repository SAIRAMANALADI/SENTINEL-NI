# Sensor Health Contract

Sentinel reports three separate health planes for every remote sensor:

1. **Agent Health** — whether a registered agent has sent a recent heartbeat.
2. **Telemetry Health** — whether the central API has accepted recent state
   telemetry.
3. **Forecast Health** — whether the sensor runtime has ten valid contiguous
   states and a computed K=5 forecast.

## Lifecycle

| Lifecycle | Meaning |
| --- | --- |
| `REGISTERED` | Identity exists; no heartbeat has been received. |
| `ONLINE` | Heartbeat and accepted telemetry are both fresh. |
| `DEGRADED` | Heartbeat is fresh but telemetry is absent or stale. |
| `OFFLINE` | Heartbeat is absent or older than the configured heartbeat timeout. |

The thresholds are central configuration, not browser refresh timing. A
reachable central API with an `OFFLINE` sensor is different from
`BACKEND_UNAVAILABLE`. A fresh heartbeat with stale telemetry is `DEGRADED`, not
`ONLINE`.

Forecast health is `WAITING` until ten same-day, contiguous ten-second states
are accepted. Existing forecast output is never relabeled as current when the
sensor is offline or telemetry is stale; the dashboard shows the operational
state instead.

## Fleet counts

`GET /api/v1/sensors` calculates counts from current registry/runtime state:
total, online, degraded, offline, active Predictive Warnings, and forecast
waiting. Active warnings count only the current +10s warning of sensors that
are currently `ONLINE` or `DEGRADED`; offline and stale data do not count.

## Disable semantics

An operator can disable a sensor with `POST /api/v1/sensors/{sensor_id}/disable`.
The persistent record is retained for audit and appears as `OFFLINE` with
`registration_state=DISABLED`. Existing sensor credentials are rejected for
future heartbeat, status, and telemetry calls. This is credential revocation,
not destructive deletion.
