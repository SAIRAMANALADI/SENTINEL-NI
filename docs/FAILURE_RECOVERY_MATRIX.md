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

## Phase P real-environment evidence update

| Failure | Observed behavior in this workspace | Recovery | Result | Evidence |
| --- | --- | --- | --- | --- |
| Central API outage | Automated buffering/retry contracts pass; no live agent outage was injected | Restore API and flush bounded buffer | NOT VERIFIED live | `py -m pytest -q` suite; no physical outage exercise |
| Network outage | Agent retry/buffer behavior is covered by tests; live network interruption was not injected | Restore network and allow retry/flush | NOT VERIFIED live | Automated tests only |
| Invalid credential | Authenticated HTTPS registration/telemetry path works; invalid-credential rejection remains covered by API tests | Re-register or rotate through admin lifecycle | PASS automated; NOT VERIFIED live agent | API security tests and localhost TLS run |
| Revoked credential | Registry disable/rejection is covered by security tests; no running-agent revocation exercise was performed | Revoke, observe rejection, provision replacement | NOT VERIFIED live | Security tests only |
| Malformed telemetry | The live agent initially exposed a flat-feature/API contract mismatch; it was fixed by nesting the 17 features in `TelemetryBatcher`, with a regression test | Reject malformed batches without central failure | PASS after fix | `tests/test_sensor_agent.py`; focused 28-test run |
| Capture failure | Live Wi-Fi/Npcap capture worked; no permission/interface failure was injected | Repair interface/capture permissions | NOT VERIFIED failure injection | Live collector probe |
| Agent crash | Actual agent registration, HTTPS heartbeats, and status reporting worked; controlled crash/restart recovery was not exercised | Restart the agent and verify freshness/buffer recovery | NOT VERIFIED live recovery | Actual CLI run; Ctrl-C used for cleanup |
| Central restart | Compose restart and down/up preserved the registered sensor in the host-backed registry; process-local runtime history reset as designed | Restart agents and resend contiguous states | PASS persistence; NOT VERIFIED active reconnect | Docker Compose restart/down/up exercise |
| Agent restart | Identity/config contract is covered and actual start/status worked; the Windows `stop` subcommand returned `[WinError 87]`, so Ctrl-C was used | Restart using the service manager and inspect health | NOT VERIFIED; cleanup defect observed | Actual CLI run |
| Certificate failure | Wrong CA and wrong hostname failed Python TLS verification; trusted localhost chain returned HTTP 200 | Correct CA, hostname, and certificate chain | PASS CA/hostname; NOT VERIFIED expired | Python `ssl`/`httpx` checks |
| Stale telemetry | Central reported `telemetry_status=STALE` and `forecast_status=BUILDING_HISTORY` after the run stopped/rejected states; no fabricated forecast was emitted | Restore valid contiguous telemetry | PASS observed | `/api/v1/sensors` response |
| Buffer overflow | Bounded-buffer behavior is covered by automated tests; no extended outage was run | Keep outage within reviewed bounds or adjust capacity | NOT VERIFIED live | Automated tests only |

Phase P measured Docker resource capacity only at the engine level. It did not
claim recovery time, long-run stability, or production capacity.

## Phase R remote forecast evidence update

| Failure or boundary | Result | Evidence |
| --- | --- | --- |
| Central API outage | PASS partial | Actual agent buffered four batches, retried with 1/2-second backoff, and flushed after backend restart; zero-loss and production RTO not claimed. |
| Agent outage | PASS partial | Central observed OFFLINE/STALE after stop; same identity resumed authenticated heartbeats after restart. |
| Duplicate/gapped state timestamp | PASS fail-closed | Central rejected invalid live cadence and did not advance a false contiguous L=10 history. |
| Insufficient history | NOT VERIFIED live forecast | Fresh sensor ended at `history_length=1` of `history_required=10`; no forecast was emitted. |
| L=10/K=5 forecast | NOT VERIFIED | No live LSTM update, five-row payload, score, timestamp, or dashboard forecast-ready state was produced. |
| Customer-path isolation | PASS | Independent customer HTTP service returned 200 while Sentinel backend was stopped. |
| Multi-host/five-sensor | NOT VERIFIED | Physical second host and five-sensor exercise unavailable. |
| Soak/capacity/overflow | NOT VERIFIED live | Traffic ran about 130 seconds; automated bounds passed, but no 30-minute live series or noisy-sensor exercise was run. |

Phase R did not change the implementation or claim staging/production capacity.

## Phase Q final evidence update

| Failure | Result | Evidence |
| --- | --- | --- |
| Central API outage | PASS partial | Live agent buffered four batches, retried with 1/2-second backoff, and flushed after backend restart; zero loss not claimed. |
| Network outage | NOT VERIFIED | No independent network cut was injected; central-stop exercise covered transport outage only. |
| Agent outage | PASS partial | Same sensor became OFFLINE/STALE after stop and returned to authenticated heartbeat operation after restart. |
| Central restart | PASS partial | Registry persisted across Compose restart/down-up; runtime history rebuilt below L=10. |
| Certificate failure | PASS partial | Wrong CA and hostname mismatch rejected; expired certificate not tested. |
| Customer-path isolation | PASS | Independent HTTP server returned 200 while Sentinel backend was stopped. |
| L=10 forecast recovery | NOT VERIFIED | Real Q sensor ended below ten contiguous accepted states; no forecast was emitted. |
| Five-sensor/multi-host failure | NOT VERIFIED | No second physical host or five-sensor run was available. |
| Soak/resource failure | NOT VERIFIED | Real traffic ran about 130 seconds; no 30-minute resource series. |
