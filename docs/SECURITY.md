# Security Boundaries

This document is the technical companion to the repository-level
[Security Policy](../SECURITY.md).

## Runtime boundaries

- Production configuration fails closed unless authentication is enabled and
  viewer, operator, and administrator bearer tokens are supplied.
- Live capture is opt-in and limited to metadata visible on the configured
  interface. Packet payload bytes are not retained by the live adapter.
- Mitigation is recommendation-only. Sentinel does not block traffic, change
  firewall rules, or execute operator commands.
- The current service is single-node and process-local. It is not an
  enterprise identity provider, durable audit store, or high-availability
  control plane.

## Distributed sensor controls

- one-time, expiring enrollment credentials;
- separate runtime credentials per sensor and hashed secrets in the registry;
- strict versioned schema, finite numbers, date/interval checks;
- bounded request size and per-sensor rate limits;
- duplicate and sequence-conflict protection;
- atomic bounded disk buffering;
- no raw packet payload forwarding or secret logging;
- isolated per-sensor runtime histories.

Remote telemetry is out-of-band: the monitored application continues to
receive customer traffic directly. The agent sends only completed aggregate
states over the authenticated telemetry endpoint; it does not forward raw
packets or customer payloads and does not block requests. Delivery is bounded
at-least-once with sequence/hash deduplication, not exactly-once.

## Distributed sensor deployment

Put the API behind HTTPS, use a private network or firewall allowlist, inject
role tokens through a secret manager/environment, and keep the registry path
private and backed up. Do not put credentials in source, URLs, screenshots, or
issue trackers.

## Release hygiene

Do not commit credentials, bearer tokens, private traffic, PCAPs, raw or
processed datasets, model checkpoints, generated caches, or local path data.
Use environment injection for deployment secrets. Review logs and audit output
for sensitive data before sharing them.

## Future work

mTLS, certificate rotation, OIDC/service identity, tenant isolation, central
high availability, and external durable queues are not implemented by this
release.

## Reporting

Do not disclose an exploitable vulnerability in a public issue. Use a private
GitHub security advisory or the maintainer contact described in
[SECURITY.md](../SECURITY.md).
