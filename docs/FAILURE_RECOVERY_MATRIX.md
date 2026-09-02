# Failure Recovery Matrix — Phase I

| Failure | Detection | System behavior | Operator action | Recovery evidence |
| --- | --- | --- | --- | --- |
| Central API outage | Agent transport error/failed request | Agent retains bounded state batches and retries with backoff; customer traffic is independent | Restore central API; inspect agent status/buffer | Automated outage/buffering coverage passed; physical outage not run |
| Network outage | Request failures and retry state | Collection continues locally until bounded buffer limits | Restore network; allow retry/flush | Automated retry/buffer tests passed |
| Invalid credential | Central authentication failure | Telemetry is rejected for that sensor only | Re-register/rotate through admin path | Security tests passed |
| Revoked credential | Registry disabled state | Future heartbeat/telemetry rejected; other sensors continue | Re-enable through controlled lifecycle or provision a new sensor | Security tests passed |
| Malformed telemetry | Schema/value/cadence validation | Batch rejected; central process remains available | Inspect rejection/audit details | API validation tests passed |
| Capture failure | Adapter unavailable/error status | Capture reports unavailable/error; no false forecast is emitted | Fix interface, permissions, Scapy/Npcap/libpcap | Capture failure tests passed; live host failure not soaked |
| Agent crash | Missing heartbeat/telemetry freshness | Sensor becomes degraded/offline by freshness policy | Restart agent/service | Lifecycle contracts passed; real process crash not run |
| Central restart | Process restart | Persistent identity remains; process-local runtime history rebuilds | Restart agents and resend valid contiguous states | Registry/runtime tests passed; Docker restart not run |
| Agent restart | Process/service restart | Same sensor identity and credential configuration remain; buffered delivery resumes as configured | Start the agent and inspect health | Agent lifecycle tests passed |
| Certificate failure | TLS context/verification failure | Connection rejected; no insecure production fallback | Correct CA/hostname/certificate | TLS failure/config tests passed; real certificate not run |
| Stale telemetry | Freshness timers | Sensor/telemetry state becomes degraded/stale; forecast readiness is not fabricated | Restore source or restart agent | Freshness tests passed |
| Buffer overflow | Explicit bounded-buffer limit | New unsendable data is reported/dropped according to buffer policy; host is not intentionally exhausted | Reduce outage duration/rate or increase reviewed bound | Buffer-bound tests passed |

The automated evidence above is not a substitute for a staging run. No
production recovery time, capacity, or long-run stability number is claimed.

## Phase J evidence update

| Failure | Observed behavior in this workspace | Recovery | Tested? | Evidence |
| --- | --- | --- | --- | --- |
| Central API outage | Real agent/API contract buffers delivery and later flushes it | Endpoint restored; buffered sequence is accepted | Automated only | `tests/api/test_remote_agent_e2e.py` passed |
| Agent outage | Freshness policy supports degraded/offline state transitions | Process restart preserves identity/config contract | Automated only | Sensor/agent lifecycle tests passed |
| Central restart | Persistent registry contract is covered; runtime history rebuild is documented | Reconnect and send contiguous states | Automated only | Registry/runtime tests passed |
| Certificate failure | TLS configuration rejects invalid/insecure production setup | Correct CA/hostname/certificate required | Automated only | Security/TLS tests passed |
| Multi-host failure | No physical second host was available | Requires staging hosts | No | `STAGING_VALIDATION_REPORT.md` |
| Docker outage | Docker CLI present but daemon named pipe unavailable | Start Docker Desktop or use a Linux staging host | No | `docker info` failure |
| Live capture failure | Scapy backend and interfaces discoverable; no live run selected | Configure interface and permissions | No live soak | `discover_capture_interfaces()` output |

Phase J did not measure recovery latency, sensor count under load, CPU, RAM,
queue growth, buffer growth, or production capacity.
