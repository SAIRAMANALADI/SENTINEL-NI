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

## Release hygiene

Do not commit credentials, bearer tokens, private traffic, PCAPs, raw or
processed datasets, model checkpoints, generated caches, or local path data.
Use environment injection for deployment secrets. Review logs and audit output
for sensitive data before sharing them.

## Reporting

Do not disclose an exploitable vulnerability in a public issue. Use a private
GitHub security advisory or the maintainer contact described in
[SECURITY.md](../SECURITY.md).
