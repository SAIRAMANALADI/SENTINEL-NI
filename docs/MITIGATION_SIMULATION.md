# Mitigation Simulation

## Policy

Source prioritization is recommendation-only:

| Priority | Recommendation |
|---|---|
| LOW PRIORITY SOURCE | `Monitor source` |
| MEDIUM PRIORITY SOURCE | `Consider temporary rate limiting` |
| HIGH PRIORITY SOURCE | `Consider aggressive rate limiting / investigation` |

The system does not automatically block an IP, change a firewall, alter a WAF, or claim that a source is malicious. Every output remains a `candidate source` record with measured reasons.

## Offline rate-limit simulation

`src/evaluation/rate_limit_simulator.py` accepts:

- `source_ip`
- current traffic rate
- recommended rate limit

It computes:

- original traffic rate;
- simulated allowed rate, equal to the lower of current rate and limit;
- throttled amount;
- percentage reduction.

For the deterministic example:

```text
source:              10.0.0.3
original rate:       350 req/s
recommended limit:   50 req/s
simulated allowed:   50 req/s
throttled amount:    300 req/s
reduction:           85.7142857%
```

This is arithmetic only. No network or firewall state is touched.

## Future integrations

After human review and a separately approved control plane, the recommendation could be translated into a temporary policy for a firewall, WAF, API gateway, or rate-limiting service. That future integration must require explicit authorization, expiry, audit logging, rollback, and evidence that the source identity is appropriate for the control action.
