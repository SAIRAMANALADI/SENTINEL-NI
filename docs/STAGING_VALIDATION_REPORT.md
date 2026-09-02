# Phase J Staging Validation Report

## A. Environment

- Windows 11 Home Single Language, build 10.0.26200.
- Python 3.14.3; `sentinel-agent 0.2.0`.
- Scapy 2.7.0 with `conf.use_pcap=True`.
- Nine local interfaces were discoverable, including Wi-Fi, Ethernet, and
  loopback. No production capture interface was selected.
- Docker CLI 29.6.2 and Compose v5.3.1 are installed; the Docker Desktop Linux
  daemon is unavailable.
- No second physical host, Linux host, staging DNS name, reverse proxy, or
  staging certificate/CA was available.

## B. Central server and topology

The intended topology remains out of band:

```text
Customer application ------------------------------> customer response path
        |
        v
Remote Agent A -- HTTPS/reverse proxy --> Central Sentinel API :8000 internal
Remote Agent B -- HTTPS/reverse proxy --> Central Sentinel API :8000 internal
```

The application path does not depend on Sentinel. The agent and central
components are implemented for this topology, but this Phase J run did not
deploy a real staging network.

## C. Reverse proxy and TLS

**NOT VERIFIED.** No staging reverse proxy or certificate was available. The
agent's production configuration still requires HTTPS and certificate
verification; the existing TLS tests cover validation behavior, wrong trust,
hostname/expiry handling at the TLS-context contract level, and reject an
insecure production configuration. No `verify=False` or `curl -k` path was
used as validation.

## D. Sensor hosts and sources

Physical multi-host validation: **NOT VERIFIED**.

The only physical host was the Windows development machine. Existing automated
tests exercise isolated sensor identities and runtimes in one process; that is
not equivalent to Host A/Host B.

Telemetry source status remains:

| Source | Status | Phase J evidence |
| --- | --- | --- |
| Scapy/local packet capture | IMPLEMENTED | Interface discovery and pcap backend verified; no live soak |
| Remote Agent | IMPLEMENTED | Existing agent-to-central and isolation tests passed |
| Replay | IMPLEMENTED | Existing regression suite passed |
| Mock | Test/demo only | Existing regression suite passed |
| Zeek `conn.log` | PARTIAL | Phase H parser/capability tests passed |
| NetFlow | PLANNED / UNSUPPORTED | No listener or decoder; correctly not tested |
| IPFIX | PLANNED / UNSUPPORTED | No listener or template decoder; correctly not tested |

## E. Validation results

| Check | Result |
| --- | --- |
| Full pytest | **281 passed, 2 warnings** |
| Agent/sensor/security focused suite | **56 passed, 2 warnings** |
| Frontend typecheck | **PASS** |
| Frontend production build | **PASS** |
| Wheel and sdist build | **PASS** |
| Dependency-inclusive clean wheel smoke | **PASS** |
| `pip check` | **PASS** |
| `docker compose config --quiet` | **PASS** |
| `git diff --check` | **PASS** |
| Protected model/data diff | **EMPTY** |

## F. Docker runtime and network security

Docker runtime: **NOT VERIFIED**.

`docker info` returned a failure connecting to
`npipe:////./pipe/dockerDesktopLinuxEngine`. Consequently, no container
startup, health, readiness, restart, registry persistence, frontend, or
runtime-port verification is claimed. Static Compose configuration keeps the
backend binding on `127.0.0.1:${BACKEND_PORT:-8000}`, but actual bindings were
not observed because the daemon was unavailable.

## G. Agent, outage, restart, and buffering evidence

The existing automated suite passed real agent/API contract paths for
registration, authenticated telemetry, forecast readiness, buffering during a
network endpoint outage, flush/recovery, sequence continuity, sensor
isolation, credential rejection/revocation/rotation, malformed telemetry,
freshness, and restart semantics. These are local automated/in-process
observations. No physical central outage, agent process outage, Docker restart,
or multi-host buffer recovery was run in Phase J.

## H. Live capture and soak

Live capture is **NOT VERIFIED** for this phase. Although Scapy/Npcap support
and interfaces are available, no interface was selected for a real capture
run. Live soak duration: **0 minutes**. Therefore packet rate, state rate,
forecast continuity, CPU, memory, queue growth, buffer growth, reconnects,
and recovery time are not reported.

## I. Dashboard and application isolation

Frontend typecheck/build passed. The backend/frontend contracts retain separate
backend-outage and sensor-outage states and sensor-scoped display data. A real
browser session with connected staging sensors and a controlled application
server was not available; no online/degraded/offline screenshot or latency
benchmark is claimed.

## J. Package, service, reboot, and upgrade

The package built successfully and an isolated dependency-inclusive wheel smoke
test verified the installed source collector registry. CLI version/help and
configuration contracts are covered by the existing tests. Windows-native
service installation, Linux systemd control, OS reboot, and version-to-version
upgrade were not executed. Only one agent version is present.

## K. Model integrity

The protected diff was empty for model weights, model/inference code, scaler,
17 features, target, L=10, K=5, threshold `0.19`, ingestion, datasets,
frozen schema, and data contract. No ML/data changes were made in Phase J.

## L. Performance and blockers

No capacity or production performance number is reported. The remaining
blockers are Docker daemon access, trusted staging TLS/DNS/reverse proxy,
physical multi-host access, a selected live capture interface, and a controlled
application server for out-of-band latency verification.

## Readiness classification

**DEVELOPMENT READY**

Phase J did not reach `STAGING READY` because the real staging prerequisites and
runtime checks were unavailable. Do not claim production readiness from this
report.
