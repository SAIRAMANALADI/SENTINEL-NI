# Sensor Control Plane Implementation Report

**Phase:** B — sensor identity and secure registration
**Date:** 2026-09-02

## Scope

Phase B hardens the sensor control plane only. The LSTM, model artifacts, 17
state features, target, operating threshold, local capture behavior, replay,
and existing telemetry/data contracts were not redesigned.

## 1. Sensor identity design

`SensorRegistry` generates a persistent `sensor-<16 hexadecimal characters>`
identity. Identity is independent of hostname and IP address. The registry
stores the identity, hostname, registration timestamps, agent version,
registration state, freshness metadata, sequence metadata, and non-secret
credential metadata. A sensor remains the same sensor across agent restarts
because the ID and runtime credential are persisted in the agent configuration.

The registry now has schema version `1`, explicit configurable storage through
`SIH_SENSOR_REGISTRY_PATH`, safe missing-file initialization, corruption/empty
file rejection, and atomic replacement writes.

## 2. Enrollment design

An administrator creates an expiring, one-time enrollment credential through
the admin-protected `POST /api/v1/sensors/enrollment` control-plane operation.
The agent consumes it once through `POST /api/v1/sensors/register`. Registration
returns a persistent sensor ID and a runtime credential once. Reuse of the
enrollment credential is rejected.

The browser no longer calls the admin enrollment endpoint. `SensorFleet` now
shows the five-step connection workflow and agent commands using a placeholder
for the one-time credential. Administrative enrollment remains a server-side
operation; no global admin token is placed in browser code, URLs, installation
commands, logs, or sensor GET responses.

## 3. Credential model

The three credential concepts remain separate:

| Credential | Purpose | Exposure/storage |
| --- | --- | --- |
| Enrollment credential | one-time bootstrap authority | returned to the administrator once; consumed at registration |
| `sensor_id` | routing and ownership identity | safe operational metadata |
| Runtime sensor credential | heartbeat and sensor-scoped operations | returned once at registration; SHA-256 hash stored centrally; redacted in agent status |

User roles remain bearer-token based: `VIEWER`, `OPERATOR`, and `ADMIN` are
ordered by the existing RBAC implementation. `SENSOR` is a separate credential
class carried in `X-Sentinel-Sensor-Token`.

## 4. RBAC changes

The existing viewer-only `GET /api/v1/sensors/{sensor_id}` endpoint remains
unchanged for operators/viewers. A sensor now uses the dedicated
`GET /api/v1/sensors/{sensor_id}/status` endpoint and can only read its own
operational metadata. A sensor credential cannot list sensors, create an
enrollment, access the model endpoint, or read another sensor's status.

`SensorClient.status()` now uses the dedicated sensor endpoint, fixing the
previous authenticated-production mismatch without weakening user RBAC.

## 5. Registry persistence

The registry location is configurable and defaults to:

```text
results/sensors/registry.json
```

Docker Compose mounts `/app/results/sensors` to the persistent host-backed
`./results/sensors` directory. Keep that directory private and backed up. The
registry file is written via an atomic temporary-file replacement.
Cross-process/HA registry behavior is not claimed.

## 6. HTTPS and server URL behavior

`AgentConfig` now validates URL scheme, host, port, embedded credentials, query
strings, fragments, and malformed URLs. It has an explicit `development` or
`production` environment:

- development permits HTTP for local use;
- production fails closed unless the central URL uses HTTPS;
- HTTP is never silently upgraded or downgraded.

The agent CLI accepts `--environment development|production`. mTLS and
certificate rotation are not implemented or claimed in this phase.

## 7. Docker persistence validation

`docker compose config --quiet`: **PASSED**.
`docker info`: **BLOCKED** — Docker Desktop's Linux engine was unavailable in
the validation environment.
The required live sequence—register, restart, down/up, and verify the same
sensor—was therefore not executed and is not claimed as passing.

## 8. Frontend changes

`frontend/components/SensorFleet.tsx` now represents the control-plane flow
without browser enrollment authority. It supports no registered sensors,
registered/pending sensors, actual health states, selection, freshness, and
agent setup commands. Registration alone is represented as `REGISTERED`; the
backend reports `ONLINE` only after actual heartbeat and telemetry freshness.

`frontend/lib/types.ts` includes the `REGISTERED` state. No dashboard redesign
or forecast behavior changed.

## 9. Tests executed

- Focused Phase B and regression tests: **22 passed**.
- Full Python suite: **231 passed**.
- Frontend `npm run typecheck`: **passed**.
- Frontend `npm run build`: **passed**.
- `docker compose config --quiet`: **passed**.
- `git diff --check`: **passed**.
- Docker persistence lifecycle: **not executed; Docker daemon unavailable**.

Focused coverage includes registry persistence and corruption handling,
registered/online/degraded/offline transitions, sensor-scoped status/RBAC,
credential redaction, enrollment isolation, production HTTPS policy, URL
validation, Compose volume declaration, and absence of browser admin-token
enrollment calls.

## 10. Limitations

- Docker daemon validation is blocked until Docker Desktop is running.
- The registry is JSON-backed and safe for the current single-process deployment,
  not multi-process HA.
- Remote runtime histories remain in memory and rebuild after central restart.
- mTLS, OIDC, certificate rotation, and a production user/session control plane
  remain future hardening work.
- Remote telemetry and source attribution were not extended in Phase B.

## 11. Exact next phase

**Phase C — telemetry transport and central runtime hardening:** execute the
Docker registry persistence test, define restart/rebuild semantics, add
sensor-scoped ingestion observability, and validate the existing telemetry
contract without changing the model or feature schema.
