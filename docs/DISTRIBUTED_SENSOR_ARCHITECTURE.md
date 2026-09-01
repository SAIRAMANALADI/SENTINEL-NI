# Distributed Sensor Architecture

Sentinel supports remote-server collection without changing the frozen
forecasting contract. A sensor runs beside the monitored interface, converts
packet metadata into completed bidirectional flows, aggregates the flows into
the existing 10-second state schema, and sends only state telemetry to the
central API.

```text
remote server: interface -> Scapy/Npcap -> LiveTelemetryAdapter
  -> FlowBuilder -> aggregate_flow_window (17 features)
  -> bounded batch + disk buffer == authenticated HTTPS ==>
central server: sensor registry -> validation -> isolated sensor runtime
  -> StateBuffer (L=10) -> existing LSTM K=5 -> dashboard
```

## Identity and enrollment

An administrator creates a short-lived, one-time enrollment credential. The
agent exchanges it for a persistent `sensor_id` and a dedicated runtime token.
The three values are distinct: enrollment is bootstrap authority, sensor ID
is routing identity, and the runtime token is sent only in
`X-Sentinel-Sensor-Token`. The registry stores only a SHA-256 runtime-token
hash. Secrets are returned once and redacted from agent output.

## Telemetry contract

Schema version `1` contains `sensor_id`, monotonic batch `sequence`, UTC
`sent_at`, and one to sixty states. Each state contains the exact frozen 17
feature names, `timestamp`, and `capture_day`. States must be finite,
date-consistent, and contiguous at ten-second intervals inside one batch.
Target columns and raw packet payloads are not accepted.

Identical accepted sequence/hash pairs are acknowledged without re-running
inference. Conflicting or out-of-order sequences are rejected. Each sensor
gets its own runtime and history; it cannot overwrite local history or another
sensor's history.

## Reliability and health

The agent batches states and stores failed batches in an atomic,
sequence-ordered disk queue. Queue count and bytes are capped. A full queue
raises an explicit error rather than discarding telemetry. Heartbeats carry
buffer count and agent version. Central status is `ONLINE` when heartbeat and
telemetry are fresh, `DEGRADED` when one is stale, and `OFFLINE` when last
seen exceeds the heartbeat timeout.

## Security and limitations

Use HTTPS behind a private reverse proxy, firewall/private-network rules, and
environment-injected role tokens. Current controls include strict schema and
size/rate validation, credential separation, secret redaction, no raw payload
logging, and per-sensor runtime isolation. mTLS, OIDC, tenant isolation, HA
registry, and external durable queues are future hardening work.

Local `MOCK`, `REPLAY`, and host-level `LIVE` modes remain unchanged. Remote
telemetry is an additional sensor path. The dashboard explicitly labels a
connected server as a sensor and never implies central capture of its packets.
