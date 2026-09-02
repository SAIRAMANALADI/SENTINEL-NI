# Security Policy

## Supported versions

The current supported public line is `0.1.x`. Security fixes are evaluated
against the current `main` branch and the latest tagged release. Older,
unmaintained snapshots should be upgraded before reporting a deployment issue.

## Reporting

Report vulnerabilities through a private GitHub security advisory for
[SAIRAMANALADI/SENTINEL-NI](https://github.com/SAIRAMANALADI/SENTINEL-NI/security/advisories/new).
Include the affected version or commit, deployment mode, reproduction steps,
impact, and any logs with secrets removed. Do not publish credentials, private
traffic, PCAP contents, or an exploitable vulnerability in a public issue.

We ask reporters to allow reasonable time for triage and coordinated
disclosure. This project does not promise a fixed response or remediation
time.

## Deployment boundary

The development profile may run without authentication for local use. The
production profile fails closed unless `SIH_AUTH_ENABLED=true` and viewer,
operator, and admin tokens are supplied. Put TLS, trusted ingress, rate
limits, secret injection, and log access controls at the deployment boundary.

The current bearer-token implementation is not an OIDC provider and is not a
substitute for enterprise identity, rotation, revocation, or penetration
testing. Recommendations never execute firewall changes.
