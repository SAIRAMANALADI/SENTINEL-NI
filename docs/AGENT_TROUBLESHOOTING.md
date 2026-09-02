# Sentinel Agent Troubleshooting

Start with:

```text
sentinel-agent config validate
sentinel-agent diagnostics
sentinel-agent status
```

## Common failures

| Symptom | Action |
| --- | --- |
| Configuration missing or malformed | Confirm `SENTINEL_AGENT_CONFIG`, then run `sentinel-agent init`. |
| Production HTTP rejected | Change the URL to the central HTTPS endpoint. |
| Registration rejected | Request a new one-time enrollment token; do not reuse a consumed token. |
| Capture unavailable | Install Npcap/libpcap, verify the interface, and grant capture permission. |
| Central unreachable | Check DNS, outbound firewall/TLS, central `/health`, and the bounded buffer. |
| Central shows DEGRADED | Heartbeat is fresh but accepted telemetry is stale or absent. |
| Forecast WAITING | Ten contiguous valid states have not reached the central sensor runtime. |
| Buffer full | Restore connectivity, inspect the selected overflow policy, and preserve logs. |
| systemd command unavailable | Install systemd or run the agent under an approved host supervisor. |

The agent does not open an inbound port on the monitored application server.
It observes the interface locally and sends aggregated state telemetry outbound.
