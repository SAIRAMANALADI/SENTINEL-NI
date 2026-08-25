# Mitigation Safety

Mitigation output is recommendation-only decision support.

Every recommendation must include:

- `simulation_only: true`
- `automatic_block: false`

The dashboard states: **Recommendation only — no traffic is automatically
blocked.** The policy may recommend monitoring, rate limiting, or investigation
for a candidate source, but it does not change firewall, WAF, API gateway, or
network policy.

Any future enforcement integration requires a separately approved control,
authorization boundary, audit trail, and human review. It is not part of this
system.
