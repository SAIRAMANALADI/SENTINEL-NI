# Distributed Sensor Implementation Report

Implemented: persistent hashed sensor registry; one-time enrollment;
dedicated sensor-token authentication; versioned bounded telemetry batches;
duplicate-safe sequence acceptance; freshness/rate metadata; per-sensor L=10
runtime using the existing 17-feature and LSTM K=5 path; CLI init/register/
start/stop/status/config; metadata-only packet-to-flow-to-state collection;
atomic bounded disk buffer; retry/heartbeat loop; Connected servers frontend;
and focused API/agent tests.

The model, checkpoint, target, threshold, feature names, ten-second cadence,
source attribution policy, mitigation policy, and local/replay/demo paths were
not redesigned. Remote source prioritization is not claimed from state-only
telemetry.

Central enrollment requires an authenticated administrator:

```text
POST /api/v1/sensors/enrollment
Authorization: Bearer <admin-token>
{"expires_in_seconds":600}
```

Remote server commands:

```text
python -m src.agent init --server-url https://central.example --interface Ethernet
python -m src.agent register --enrollment-token <token>
python -m src.agent start
```

## Reported implementation surface

1. Architecture: out-of-band remote agent to central API; customer requests
   remain on the application-server path.
2. Agent: `src/agent` owns config, host identity, packet metadata collection,
   flow conversion, state batching, transport, retry, and local buffer.
3. Registration: admin creates a one-time enrollment; agent registers and
   persists the server-issued sensor ID and runtime credential.
4. Authentication: role bearer tokens protect central operator/admin views;
   dedicated `X-Sentinel-Sensor-Token` protects sensor heartbeat/telemetry.
5. Telemetry: schema version `1`, monotonic sensor sequence, UTC send time,
   exact 17 features, timestamp, capture day, and max 60 states per batch.
6. Buffering: atomic JSON files, ordered by sequence, bounded by batch count
   and bytes, with exponential retry backoff for transient failures.
7. Heartbeat: independent heartbeat carries buffer count and agent version.
8. Health: registered-only sensors are OFFLINE; fresh heartbeat plus telemetry
   is ONLINE; partial freshness is DEGRADED.
9. Isolation: each sensor owns a separate state buffer, forecast context,
   sequence ledger, and health record.
10. API: enrollment, registration, sensor list/detail, heartbeat, and telemetry
    endpoints are implemented under `/api/v1`.
11. Frontend: Connected servers view supports real enrollment generation,
    server selection, health/freshness, sensor-scoped forecast context, and
    honest state-only source limitations.
12. Security: strict validation, request bounds, rate limits, duplicate
    handling, secret redaction, no raw payload forwarding, and deployment
    guidance for TLS/private networking.

## Validation

The focused remote suite covers enrollment, authentication, duplicate handling,
interval validation, rate limits, buffer ordering, config redaction, collector
retention, real LSTM ingestion, and two-sensor isolation. Final validation:
`python -m pytest -q` completed with **224 passed**. Frontend `npm run
typecheck` and `npm run build` completed successfully, and
`docker compose config --quiet` passed.

## Known limitations

A real multi-host Scapy/Npcap soak, TLS reverse-proxy deployment, mTLS, HA
registry, and service-manager packaging remain deployment work. Source
prioritization is unavailable for remote state-only telemetry because the
current remote contract intentionally does not transmit source identity.
