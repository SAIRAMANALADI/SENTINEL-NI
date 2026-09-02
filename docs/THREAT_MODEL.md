# Sentinel Threat Model

This is an engineering threat model for the current single-node release, not
a certification or penetration-test report.

| Threat | Current mitigation | Residual risk | Future mitigation |
|---|---|---|---|
| Stolen sensor credential | HTTPS, per-sensor token hash, disable and rotation | Bearer token can be used until revoked | mTLS/device-bound identity, short-lived signed tokens |
| Sensor impersonation | Token is checked against the requested sensor ID | Compromise of the real host remains authoritative | Hardware-backed identity and attestation |
| Telemetry replay | Monotonic sequence, batch hash, duplicate acknowledgement | New-sequence semantic replay is not cryptographically prevented; delayed data is allowed | Signed nonce/timestamp envelopes |
| Telemetry tampering | HTTPS, Pydantic finite/shape/cadence validation | A compromised agent can send valid-looking data | Signed telemetry and independent attestation |
| Central API exposure | Loopback Compose binding, reverse-proxy guidance, role auth | Deployment firewall/proxy mistakes remain possible | Managed ingress and network policy |
| Malicious remote host | Out-of-band agent, no remote command channel | Host can stop or alter its own agent | Host hardening and attestation |
| Malicious operator | Role separation and append-only audit | Admin can rotate/disable sensors | Dual control and external audit sink |
| Secret leakage | No frontend token, URL token, payload/log/audit secret, redacted diagnostics | Windows ACL enforcement is operator-owned | OS secret vault and secret manager |
| Resource exhaustion | Request/body/state bounds, per-sensor and registration limits | Current limits are process-local | Distributed gateway limiting and queue isolation |
| Stale telemetry | Heartbeat/telemetry freshness planes and stale status | A fresh heartbeat does not prove fresh data | Signed freshness and alerting policy |
| Cross-sensor contamination | Credential-bound identity and isolated runtime histories | Single process remains a shared failure domain | Tenant-aware durable isolation |

Customer traffic is outside Sentinel's trust boundary: the agent observes in
parallel and never proxies application requests or responses. Automatic blocking,
OIDC, HA, Kafka, PKI issuance, and remote arbitrary execution are not part of
this release.
