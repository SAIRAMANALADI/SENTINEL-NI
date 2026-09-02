# Deployment Test Matrix — Phase I

This matrix records what was actually available and tested in the Phase I
workspace. A green automated test is not presented as proof of a physical
multi-host or production deployment.

| Area | Actual environment | Result |
| --- | --- | --- |
| Central OS | Windows 11 Home Single Language, build 10.0.26200 | Tested locally |
| Central Python | Python 3.14.3 | Tested |
| Docker | CLI 29.6.2 / Compose v5.3.1; Linux engine unavailable | Compose config PASS; runtime BLOCKED |
| Reverse proxy | No nginx, Caddy, Traefik, or HAProxy detected | Not tested |
| Staging TLS | No staging DNS, certificate, CA, or reverse proxy available | Not tested |
| Remote sensor host | Same Windows development host and isolated test fixtures | Automated only; not a second physical host |
| Capture backend | Scapy 2.7.0 with `conf.use_pcap=True` | Capture contract/regression tested; no live permission soak |
| Interface | No selected production capture interface configured | Not tested |
| Agent | `sentinel-agent 0.2.0` | CLI/package and in-process HTTP path tested |
| Telemetry | Remote Agent schema version 1; local/replay/mock paths | Automated tests passed |
| Source abstraction | Scapy, Remote Agent, Replay, Mock implemented; Zeek partial; NetFlow/IPFIX unsupported | Contract tests passed |

## Topology

The intended staging topology is:

```text
Customer application  ------------------------------> customers
        |
        | observed out of band
        v
Remote sensor / Agent A ---- TLS ----> Central Sentinel API :8000 (internal)
Remote sensor / Agent B ---- TLS ----> Central Sentinel API :8000 (internal)
                                              |
                                              v
                                  registry + sensor runtime + dashboard
```

The customer request path does not traverse Sentinel. In this workspace only
the central/agent contracts and in-process HTTP tests were exercised. No claim
is made that the topology above was deployed across two physical hosts.

## Evidence boundaries

- **Actually tested:** 281 pytest tests, including agent-to-central,
  multi-sensor isolation, restart/buffering/security contracts; package build,
  clean wheel smoke, frontend checks, and Compose configuration.
- **Not tested:** real staging certificate chain/hostname/expiry, reverse proxy,
  Docker service startup/restart/health, physical multi-host operation, live
  packet capture soak, and 30-minute sustained operation.
- **Known environment blocker:** `docker info` cannot connect to the Docker
  Desktop Linux engine named pipe.
