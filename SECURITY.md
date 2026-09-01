# Security Policy

## Reporting

Do not publish credentials, private traffic, PCAP contents, or an exploitable
vulnerability in a public issue. Contact the repository maintainers through a
private GitHub security advisory or the private channel configured by the
project owner.

## Deployment boundary

The development profile may run without authentication for local use. The
production profile fails closed unless `SIH_AUTH_ENABLED=true` and viewer,
operator, and admin tokens are supplied. Put TLS, trusted ingress, rate
limits, secret injection, and log access controls at the deployment boundary.

The current bearer-token implementation is not an OIDC provider and is not a
substitute for enterprise identity, rotation, revocation, or penetration
testing. Recommendations never execute firewall changes.
