# Sentinel Security Architecture

Phase G establishes the security boundary for the distributed sensor release.
It does not change the frozen model, 17-feature state contract, L=10 history,
K=5 forecast, threshold, or recommendation-only operating policy.

## Trust boundaries

```text
Customer -> Company application server
                |
                | parallel observation only
                v
         Sentinel Agent -- HTTPS --> TLS reverse proxy -- internal --> API :8000
                                               |
                                               v
                                   sensor registry + sensor-scoped runtime
```

Customer requests and application responses never pass through Sentinel. The
agent captures locally, creates the existing aggregate state, and sends only
validated telemetry. Sentinel is not a customer traffic proxy, inline firewall,
or packet payload relay.

## Identity and authorization

An administrator creates a short-lived, one-time enrollment credential. The
registration endpoint consumes it and returns a persistent `sensor_id` plus a
sensor-specific runtime credential exactly once. The registry stores only a
SHA-256 hash of the runtime credential. Every heartbeat and telemetry request
uses `X-Sentinel-Sensor-Token`; the JSON `sensor_id` is checked against the
credential-bound identity. Role bearer tokens are separate and cannot be used
as sensor credentials.

Viewer, operator, and admin roles remain separate. Sensor credentials can read
only their own status and can submit only their own telemetry. Admin-only
enrollment and credential rotation are never called by the frontend.

## Lifecycle controls

- Disable is non-destructive: the record remains, is shown as `OFFLINE`, and
  authentication fails for future requests.
- Rotation issues one replacement token for an active sensor, invalidating the
  old token immediately while preserving `sensor_id`, history, and health.
- Rotation output is a one-time control-plane response for an administrator;
  delivery to the agent is out of band and requires an operator restart/update.
- Disabled sensors cannot be silently re-enabled or rotated.

## Transport

Production agent configuration requires HTTPS and certificate verification.
The standard Python TLS context validates the certificate chain, hostname, and
expiry. A custom CA bundle and optional client certificate/key can be supplied
explicitly. The latter is an mTLS-ready interface, not an implemented PKI or
mTLS deployment. TLS verification can be disabled only in explicitly configured
development mode; production rejects that configuration.

## Replay, resource, and audit controls

Telemetry is versioned, finite, same-day, contiguous at 10 seconds, bounded to
60 states per batch, bounded by request body size, rate-limited per sensor, and
protected by monotonic sequence plus batch-hash duplicate handling. Delayed
delivery is supported by the agent buffer. This prevents indefinite replay of
an accepted sequence but is not cryptographic anti-replay; a future release
would need signed envelopes/nonces for that guarantee.

Security events are append-only JSONL records containing event type, result,
reason, request ID, sensor ID where known, and source address where appropriate.
Secrets, authorization headers, private keys, and telemetry payloads are not
written to logs or audit records.

## Deployment posture

Compose binds the API port to loopback. Production deployments should place a
TLS reverse proxy in front of it and keep port 8000 off the public interface.
The current limiter and registry are process-local/single-node; HA storage,
distributed rate limiting, OIDC, and mTLS are future work.

The central API transport policy is explicit:

- `development_http` permits local HTTP only in `development` or `test`.
- `direct_https` requires the request scheme to be HTTPS and ignores forwarded
  protocol headers.
- `trusted_proxy` permits internal HTTP only when the peer address is inside
  `SIH_TRUSTED_PROXY_CIDRS` and `X-Forwarded-Proto` is exactly `https`.

Production defaults to `direct_https`; production cannot use
`development_http`. Loopback `/api/v1/health` and `/api/v1/ready` probes remain
available over internal HTTP for orchestration. Forwarded headers from an
untrusted peer never satisfy the HTTPS requirement.
