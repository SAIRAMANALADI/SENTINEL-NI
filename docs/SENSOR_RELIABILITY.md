# Sensor Reliability — Phase D

Phase D hardens the existing authenticated remote sensor path without changing
the frozen 17-feature state contract, L=10 history, LSTM K=5 forecast, target,
threshold, or local/replay/mock behavior.

## Delivery boundary

```text
capture -> flow -> 10-second state -> bounded local queue -> authenticated API
                                                        -> sensor-scoped runtime
                                                        -> existing forecast
```

The queue is local to one agent. Customer application requests never pass
through this path and never wait for telemetry delivery or forecast inference.

## Buffer and persistence

`src/agent/buffer.py` stores each unsent envelope as an atomically replaced,
sequence-named JSON file. The default bound is 256 batches or 64 MiB,
whichever is reached first. `DROP_OLDEST` is the default explicit overflow
policy; `REJECT_NEW` is available for deployments that prefer back-pressure.
Evictions are counted in local status and logs. A batch larger than the byte
limit is rejected rather than split or silently discarded.

The queue survives a normal agent restart because files remain on disk. A
leftover temporary write is moved to `quarantine/partial-*`. A malformed
queued envelope is moved to `quarantine/corrupt-*`; it is never acknowledged
as delivered. Permanently rejected envelopes receive a small diagnostic record
under `rejected/` and are removed from the retry queue.

This is bounded local durability, not exactly-once delivery or a distributed
queue. The current central runtime history remains process-local and must be
rebuilt after a central process restart.

## Retry and reconnect

Network errors, timeouts, HTTP 408, 425, 429, and 5xx are transient. They are
retried in sequence order with exponential backoff. The default delay starts
at 1 second and is capped at 60 seconds; optional non-negative jitter can be
configured. A successful send resets the delay and the next queued envelope is
attempted.

HTTP 400, 401, 403, 422, and other non-transient responses are permanent for
the current payload. They are surfaced in status/logs, recorded under
`rejected/`, and are not retried forever. The agent loop remains alive so
collection is not coupled to a single rejected upload.

## Heartbeat and health

Heartbeat is an independent authenticated request. It reports the sensor ID,
agent version, capture status, buffered count/bytes, last state timestamp,
sequence progress, and the last error category/message. It never sends the
runtime credential in the body, logs, or URL.

Central health deliberately separates three layers:

| Layer | Meaning |
| --- | --- |
| Agent | Recent heartbeat from the registered process |
| Telemetry | Recent accepted telemetry at the central API |
| Forecast | The sensor runtime has ten valid contiguous states and a current forecast |

Lifecycle remains `REGISTERED`, `ONLINE`, `DEGRADED`, `OFFLINE`:

- `REGISTERED`: identity exists but no heartbeat has been received.
- `ONLINE`: heartbeat is within the configured heartbeat timeout and accepted
  telemetry is within the configured telemetry freshness window.
- `DEGRADED`: heartbeat is fresh but telemetry is absent or stale.
- `OFFLINE`: heartbeat is absent or older than the heartbeat timeout.

The dashboard renders agent, telemetry, and forecast health separately. A
reachable central API with an offline sensor is not the same as a central API
outage. A sensor with fresh heartbeat but stale telemetry is degraded, not
online.

## Sequence semantics

The agent persists the next sequence number before sending a newly built
envelope. The central registry stores the last accepted sequence and payload
hash per sensor. An identical retransmission receives
`DUPLICATE_ACKNOWLEDGED` without running inference twice. Older or conflicting
sequences are rejected. Delivery is bounded at-least-once with deduplication;
the system does not claim exactly-once delivery.

## Late data and forecast readiness

State timestamps remain the capture timeline. `sent_at`, heartbeat receipt, and
central telemetry freshness describe delivery/arrival time and do not rewrite a
state timestamp. The central runtime preserves strict ten-second, same-day
ordering. Gaps reset the sensor history without interpolation. Forecast output
is withheld until the sensor has ten valid contiguous states.

## Security and limitations

Production agent configuration requires HTTPS. The registry stores only a
SHA-256 runtime-token hash. Role bearer credentials and sensor credentials are
separate. Raw packet payloads are not retained or sent. Aggregate remote states
do not contain source identity, so remote candidate-source attribution remains
unavailable and no source or mitigation action is fabricated. Automatic
blocking is out of scope.
