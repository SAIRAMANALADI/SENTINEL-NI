# Mitigation

Mitigation is recommendation-only in the current release. Responses include:

```json
{
  "simulation_only": true,
  "automatic_block": false
}
```

Recommendations can suggest monitoring, investigation, or consideration of
rate limiting. Sentinel does not change firewall rules, block traffic, or
execute operator commands. Any future enforcement integration requires a
separate security review, explicit authorization, and an audited policy.
