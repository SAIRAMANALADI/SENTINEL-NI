# Sentinel Subagent 4 — Security Review

**Review date:** 2026-09-04  
**Scope:** Current working tree in `SIH26/1`, including the uncommitted
remote-sensor, source-telemetry, agent, API, and frontend changes from the
other subagents. The review covers authentication, authorization, sensor
identity and isolation, TLS, secret exposure, replay, limits, Docker exposure,
command execution, and logging. ML weights and data files were not edited.

No source changes were made by this review; only this document was added. No
commit or push was performed.

## Executive result

No CRITICAL issue was identified. HIGH-1 through HIGH-4 were remediated at the
application-policy level in the coordinator integration and Phase O passes.
Production deployment remains conditional because live TLS termination,
reverse-proxy forwarding, and Docker runtime behavior were not exercised here.

## Findings

### HIGH-1 — Frontend bearer credential exposure

**Evidence:** The pre-integration client read
`process.env.NEXT_PUBLIC_SIH_API_TOKEN` and added it to every browser request.
The coordinator removed that client-side path and added an allowlisted
server-side proxy at `frontend/app/api/[...path]/route.ts`.

**Impact:** Any user who can load the frontend can inspect the bundle or browser
network requests and recover the configured token. If an operator or admin
token is supplied, this becomes control-plane privilege escalation; even a
viewer token exposes all viewer-authorized sensor and telemetry data to every
browser user. This describes the pre-integration risk; the current client no
longer embeds the token.

**Remediation/status:** **RESOLVED in the coordinator integration pass.** The
browser client no longer reads `NEXT_PUBLIC_SIH_API_TOKEN`; requests use an
allowlisted server-side Next route, which reads only server-side
`SIH_API_TOKEN`. The browser bundle contains no bearer credential. Production
still requires a separately configured server-side role token or external
session boundary.

### HIGH-2 — Request-size limit is bypassable for chunked bodies

**Evidence:** Before integration, `src/api/app.py` rejected only when a supplied
`Content-Length` exceeded `settings.max_request_bytes`. The coordinator added
ASGI-stream counting before FastAPI body parsing.

**Impact:** A remote client can send a chunked or otherwise lengthless body
larger than the configured 2 MB limit and force body buffering, JSON parsing,
Pydantic validation, and audit/error handling. Repeated requests can consume
memory/CPU and degrade or terminate the API before endpoint authentication or
business limits run.

**Remediation/status:** **RESOLVED in the coordinator integration pass.** The
middleware counts the ASGI body stream and stops at the configured limit even
when `Content-Length` is absent. Declared-length and chunked paths are covered
by `tests/api/test_security_hardening.py`.

### HIGH-3 — Default Docker dashboard is network-exposed without authentication

**Evidence:** Before integration, `docker-compose.yml:35-54` published the
Streamlit dashboard as `${DASHBOARD_PORT:-8501}:8501` without a loopback host
binding. The dashboard calls the backend with an optional blank token at
`docker-compose.yml:40-41`; the backend is therefore unauthenticated under
the default profile. The dashboard contains control calls at
`app/streamlit_app.py:729-735` and demo orchestration at
`app/streamlit_app.py:503-518`.

**Impact:** Any host able to reach the published dashboard can use the UI to
invoke backend-mediated operator actions and view sensor/forecast data. This
is an unsafe default if Compose is started on a shared LAN, cloud VM, or
otherwise non-local host.

**Remediation/status:** **RESOLVED for default Compose exposure in the
coordinator integration pass.** The dashboard now publishes on `127.0.0.1` by
default, matching the backend/frontend loopback bindings. Docker daemon
startup, network reachability, and runtime behavior remain unverified, and a
production deployment still needs an authenticated TLS boundary.

### HIGH-4 — Central API did not fail closed on plaintext HTTP (resolved)

**Pre-Phase-O evidence:** Production agent configuration required an HTTPS
destination at `src/agent/config.py:189-190` and certificate verification at
`src/agent/config.py:226-227`, but the central API accepted direct plaintext
HTTP when production authentication was enabled.

**Impact:** An operator can run the API with production role authentication
over plaintext HTTP, or expose the container without the documented TLS
terminator. Bearer tokens, sensor runtime tokens, and telemetry can then be
captured or modified in transit. The agent’s HTTPS checks do not protect
browser/admin callers or an incorrectly exposed API.

**Remediation/status:** **RESOLVED at the application policy level in Phase O.**
`SIH_TRANSPORT_MODE=direct_https` requires the ASGI request scheme to be HTTPS;
`trusted_proxy` requires an immediate peer in `SIH_TRUSTED_PROXY_CIDRS` and an
exact `X-Forwarded-Proto: https` value. Untrusted forwarded headers do not
satisfy the policy, and production cannot select `development_http`. Loopback
health/readiness is retained for internal service checks. Focused production,
trusted-proxy, forged-header, authentication, registration, telemetry, and
internal-health tests pass in `tests/api/test_https_enforcement.py`.
Live staging TLS, certificate/hostname validation, ingress behavior, and
container reachability remain unverified deployment boundaries.

### MEDIUM-1 — Failed-authentication audit writes are unbounded and not rate-limited

**Evidence:** Auth failures synchronously call the audit logger from
`src/api/auth.py:17-33` and `src/api/sensors.py:16-29`. `AuditLogger.record()`
appends without a size/rotation limit at `src/platform/audit.py:60-63`.
Failed sensor authentication is processed before the per-sensor request
limit, while the authenticated limit is only checked later at
`src/sensors/registry.py:273-283`. The audit directory is a writable host
volume at `docker-compose.yml:21-26`.

**Impact:** An unauthenticated attacker can generate repeated invalid bearer or
sensor-token requests and fill the audit volume, increase synchronous disk I/O,
and obscure useful security events. This can become a persistent availability
failure even though valid sensor traffic has a per-sensor rate limit.

**Remediation/status:** Add a bounded global/IP-based failed-auth limiter,
avoid synchronous unbounded writes on the request path, and rotate/size-limit
the audit sink with an explicit retention policy. Keep audit records secret
safe. **OPEN.** No flood or disk-capacity test was run.

### MEDIUM-2 — Replay protection is delivery-order protection, not freshness/authenticity

**Evidence:** `src/api/app.py:620-627` hashes the body and calls
`check_telemetry`; `src/sensors/registry.py:316-326` accepts any sequence higher
than the last accepted sequence and acknowledges an exact duplicate. The only
`sent_at` check is timezone awareness at `src/api/models.py:261-266`; there is
no freshness window, nonce, signature, or binding between event time and
receipt time. The repository’s own threat model acknowledges the residual at
`docs/THREAT_MODEL.md:10`.

**Impact:** A captured valid batch can be replayed before its original delivery
or a holder of a valid sensor token can submit old event-time data with a new
sequence. Old source activity can consequently appear current because receipt
freshness is updated on ingest. This permits stale-data poisoning and alert
reordering even though ordinary duplicate retries are handled.

**Remediation/status:** Add signed envelopes or an authenticated nonce/timestamp
window, persist replay state durably, and reject event-time data outside an
explicit policy. Keep sequence/hash deduplication for transport retries.
**OPEN residual risk; cryptographic replay prevention is not implemented.**

### MEDIUM-3 — Live source aggregation has no per-window event bound

**Evidence:** `src/streaming/source_activity.py:187-215` appends every
normalized packet to `_events` until the ten-second bucket changes; there is no
maximum event count or byte budget. The live agent enables this callback at
`src/agent/client.py:402-406`. Separately, active flows retain unbounded packet
length and inter-arrival lists at `src/streaming/flow_builder.py:60-65` and
`src/streaming/flow_builder.py:80-82`.

**Impact:** A high-rate interface or hostile traffic pattern can make the
agent retain a very large in-memory packet/event sample during one window or
one long-lived flow, causing local memory and CPU exhaustion. The bounded
outbound queue and central batch limits do not constrain this pre-batch local
state.

**Remediation/status:** Add explicit per-window/per-flow event and byte caps,
with a documented drop/aggregation policy and counters, before appending to
these collections. **OPEN; no high-rate live-capture soak was run.**

### MEDIUM-4 — Validation errors reflect submitted enrollment secrets

**Evidence:** Before integration, `SensorRegisterRequest` validation reflected
secret inputs in generic 422 responses. The coordinator now sanitizes
secret-bearing validation locations before serialization.

**Impact:** A malformed/too-short enrollment secret can be reflected into
client logs, browser error state, proxy traces, or support captures. The caller
already supplied the secret, but reflection expands its exposure and conflicts
with the secret-safe contract.

**Remediation/status:** **RESOLVED in the coordinator integration pass.** The
validation handler removes secret inputs and returns a stable generic message;
the regression test covers invalid enrollment. The successful registration
path does not log the token, and the agent transport deliberately suppresses server error bodies at
`src/agent/transport.py:80-86`.

## Low-severity observations

### LOW-1 — Readiness failure details can disclose local paths

`/api/v1/ready` is unauthenticated at `src/api/app.py:796-801`, while
`Runtime.readiness()` returns configuration/schema/policy/model failure reasons
at `src/api/app.py:113-145`. Several configuration errors include absolute
paths. In a failed deployment this gives unauthenticated callers filesystem
layout and operational details. Return a generic public readiness state and
keep detailed reasons behind an authenticated operator endpoint. **OPEN.**

### LOW-2 — Logging redaction is a denylist, not a structured secret policy

`src/platform/logging.py:86-88` drops only exact field names
`token/password/secret/payload`. It does not recursively redact nested values,
authorization headers, private-key fields, or names such as `runtime_token`.
Current reviewed call sites do not pass those secrets to `log_event`, and the
JSON formatter safely escapes attacker-controlled text at
`src/platform/logging.py:17-42`; this is a forward-maintenance risk rather
than a confirmed current token leak.

## Controls reviewed and presently supported

- Role authorization is correctly applied to the tested viewer/operator/admin
  routes in `src/api/app.py:366-951`; `tests/api/test_auth_and_platform.py:38-53`
  passed.
- Sensor credentials are separate from role credentials, hashed centrally, and
  compared in constant-time at `src/sensors/registry.py:252-261`. The telemetry
  dependency binds the token to the body sensor ID at `src/api/sensors.py:49-63`.
- Cross-sensor runtime state is keyed by the authenticated sensor ID in
  `src/sensors/runtime.py:252-295`; the two-sensor impersonation/isolation tests
  passed. This is logical in-process isolation, not tenant isolation or
  multi-worker durability.
- Agent TLS verification is enabled by default and the production agent rejects
  HTTP and disabled verification (`src/agent/transport.py:23-47`,
  `src/agent/config.py:189-190,226-227`). mTLS is only an optional client-cert
  loading interface; the server does not implement client-PKI validation.
- Sequence/hash duplicate handling, bounded source/state batch models, and
  declared-length/chunked request rejection are covered by tests. These
  controls do not close the MEDIUM-2 gap above.
- The service command uses an argument list rather than shell interpolation at
  `src/agent/service.py:52-57`; the CLI constrains service actions at
  `src/agent/cli.py:70-72`. No unsafe command-execution finding was confirmed.
- React-rendered sensor/source values are escaped by React, and Streamlit’s
  dynamic display paths use `html.escape` where raw HTML is built. No confirmed
  current XSS path was found.

## Test and verification record

Executed from `SIH26/1`:

- `pytest -q tests/api/test_security_hardening.py tests/api/test_auth_and_platform.py tests/api/test_remote_sensors.py tests/test_remote_source_telemetry.py tests/test_sensor_agent.py` — **46 passed**, 3 dependency warnings.
- `pytest -q tests/api/test_remote_sensor_journey.py tests/test_next_dashboard_contract.py tests/api/test_remote_sensors.py tests/test_remote_source_telemetry.py` — **20 passed, 1 failed**. The failure is a current frontend contract mismatch in `tests/test_next_dashboard_contract.py`, not a security assertion.
- `npm run typecheck` and `npm run build` in `frontend` — **PASS** after the
  coordinator server-side proxy integration.
- `git diff --check` — no whitespace errors; line-ending warnings only.
- Phase O focused transport checks — **20 passed**; production direct HTTP and
  forged forwarded-proto requests reject, trusted-proxy and direct-HTTPS paths
  remain usable, and auth/registration/telemetry/internal-health paths remain
  covered.

## Explicitly unverified claims and boundaries

- No live browser bundle inspection, staging HTTPS handshake,
  reverse-proxy test, or certificate/hostname deployment test was completed.
- No Docker daemon run, container network reachability test, dashboard access
  test, host firewall test, or production Compose profile test was completed.
- No physical multi-host test, multi-worker Uvicorn test, restart/HA test, or
  long-running high-rate sensor soak was completed. The runtime store and
  registry are process-local; multiple workers are not established as safe.
- No penetration test, credential brute-force/flood test, audit-volume exhaustion
  test, or cryptographic replay test was
  completed.
- Windows ACL enforcement for credential files remains host-administrator
  responsibility. The agent’s mTLS client-certificate options do not prove
  server-side mTLS.
- Documentation statements such as “no frontend token,” “bounded request
  size,” “TLS certificate behavior,” and “Docker deployment” must not be
  treated as verified where they conflict with the implementation or the
  missing runtime tests above.
