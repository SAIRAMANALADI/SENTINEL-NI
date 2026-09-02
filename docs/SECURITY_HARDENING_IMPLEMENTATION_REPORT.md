# Phase G Security Hardening Implementation Report

## Scope

Phase G hardens the distributed agent-to-central connection. The frozen data
pipeline, model weights, inference implementation, 17-feature schema, target,
L=10 history, K=5 forecast, threshold, source attribution, and mitigation
semantics were not changed.

## 1. Threat model

The threat model is documented in [THREAT_MODEL.md](THREAT_MODEL.md). It covers
stolen sensor credentials, impersonation, replay/tampering, API exposure,
malicious hosts/operators, secret leakage, exhaustion, stale data, and
cross-sensor contamination. No certification, penetration test, or compliance
claim is made.

## 2. Credential lifecycle

An admin issues a short-lived one-time enrollment credential. Registration
consumes it and creates a persistent `sensor_id` plus a sensor-specific random
runtime credential. The central registry stores only its SHA-256 hash. The
agent stores the secret in a separate protected credential file. The lifecycle
details are in [CREDENTIAL_LIFECYCLE.md](CREDENTIAL_LIFECYCLE.md).

## 3. Revocation and rotation

Disable is non-destructive and immediately rejects future sensor
authentication for telemetry, heartbeat, and status. Admin-only rotation
replaces the runtime hash, preserves the sensor ID and runtime history, and
returns the replacement token once for secure out-of-band delivery. There is no
automatic rotation or grace period.

## 4. TLS behavior

The agent transport builds a standard validating Python TLS context. Production
requires HTTPS and verification; chain trust, hostname, and expiry are handled
by the TLS library. A custom CA path and optional client cert/key can be
configured. The client-cert interface is mTLS-ready, but mTLS/PKI is not
implemented. Development-only verification disablement is explicit and
production rejects it. See [TLS_DEPLOYMENT.md](TLS_DEPLOYMENT.md).

## 5. Reverse proxy model

Compose binds API `:8000` to loopback. A deployment reverse proxy should
terminate HTTPS and forward only Sentinel API traffic to the internal API. The
customer application path remains independent; Sentinel is not an inline
proxy.

## 6. Authentication and authorization

Role bearer tokens protect viewer/operator/admin control-plane actions. Sensor
runtime tokens are a separate header and are bound to one sensor identity.
Telemetry does not accept anonymous, viewer, operator, or admin credentials.
Sensor A cannot read, modify, disable, or submit telemetry for Sensor B.

## 7. Replay protection

Telemetry uses sensor identity, monotonic sequences, canonical batch hashes,
duplicate acknowledgement, same-day/10-second cadence, and bounded payloads.
Buffered delayed delivery remains valid. This prevents indefinite replay of an
accepted sequence but is not cryptographic anti-replay.

## 8. Rate limiting and resource bounds

The API enforces request body and batch-state bounds. Telemetry and heartbeat
requests are limited per sensor; registration has a separate process-local
source limit. The limits are designed so one sensor does not consume another
sensor's runtime history. Multi-worker/distributed enforcement is not
implemented.

## 9. Secret handling and audit

Tokens are excluded from configuration JSON, frontend code/responses, logs,
diagnostics, transport errors, and audit records. POSIX credential files are
written with owner-only mode where supported; Windows ACL restriction remains
an operator responsibility. Audit records include request ID, event, result,
reason, sensor ID where known, and source address where appropriate.

## 10. Multi-sensor security

Focused tests exercise two and three sensor scenarios, including credential
spoofing, disabled sensor behavior, per-sensor history isolation, rotation, and
continued operation of an unaffected sensor. The runtime store remains a
single-process failure domain.

## 11. Docker security

Compose retains `no-new-privileges`, drops all capabilities, runs the image as
the unprivileged `app` user, mounts model/config/sample inputs read-only, and
persists only the registry/audit paths that need writes. Docker daemon runtime
validation is environment-dependent and must be reported separately when the
daemon is unavailable.

## 12. Multi-host validation

No claim of real multi-host HTTPS soak or staging certificate validation is
made by this repository-only test run. A real deployment must use a trusted
certificate and reverse proxy, then validate connection, reconnect, buffering,
revocation, and rotation from separate hosts.

## 13. Verification matrix

Automated coverage added in Phase G includes:

- validating/insecure-development TLS context behavior;
- production rejection of insecure transport and invalid TLS configuration;
- safe transport context forwarding and secret redaction;
- admin-only rotation, old-token rejection, new-token acceptance, and stable
  sensor identity;
- sensor spoofing and cross-sensor forecast/history isolation;
- disabled heartbeat rejection and unaffected-sensor continuity;
- API security headers and early request-size rejection;
- existing enrollment, authentication, replay/duplicate, rate, and agent
  configuration regression coverage.

Measured Phase G validation in this workspace:

- full `python -m pytest -q`: **267 passed, 6 warnings**;
- focused Phase G security suite: **11 passed**;
- frontend `npm run typecheck`: **PASS**;
- frontend `npm run build`: **PASS**;
- `python -m build --wheel --sdist`: **PASS**;
- isolated wheel CLI smoke test (`sentinel-agent --version`/`--help`): **PASS**;
- existing environment `pip check`: **No broken requirements found**;
- a dependency-inclusive temporary clean install was attempted but package
  provisioning did not finish in this workspace; it is not claimed as passed;
- `docker compose config --quiet`: **PASS**;
- protected model/data/forecasting diff: **empty**;
- `git diff --check`: **PASS** apart from normal CRLF conversion warnings.

The Docker CLI is installed, but `docker info` cannot connect to the Docker
Desktop Linux engine, so container startup/restart/health validation is
**BLOCKED by the local daemon**. No real staging certificate or multi-host
HTTPS soak was available; those are not claimed as passed.

## 14. Limitations and future work

Not implemented: enterprise PKI/mTLS, certificate rotation automation, OIDC,
tenant isolation, distributed rate limiting, HA registry storage, external
durable audit, automatic agent code updates, remote arbitrary execution, and
automatic traffic blocking. These are intentionally outside Phase G.
