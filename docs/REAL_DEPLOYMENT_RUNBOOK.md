# Real Deployment Runbook

This runbook separates command syntax from evidence. Commands marked
**NOT EXECUTED HERE** require a real staging environment and are not validation
results for this workspace.

## Central server

### Start

```powershell
$env:SIH_ENV = "development"
$env:SIH_TELEMETRY_MODE = "mock"
python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000
```

For a production direct-HTTPS listener, configure
`SIH_ENV=production`, `SIH_TRANSPORT_MODE=direct_https`, and TLS termination
for the Uvicorn process. For the documented reverse-proxy topology, configure
`SIH_TRANSPORT_MODE=trusted_proxy` and a narrow
`SIH_TRUSTED_PROXY_CIDRS` value for the proxy's source address. Direct HTTP is
rejected in production; loopback health/readiness probes remain available for
internal orchestration.

Status: **LOCAL VALIDATION PASS** for the rebuilt Compose central services and
the isolated localhost HTTPS reverse-proxy exercise. Public staging hostname,
public CA, and production ingress remain **NOT VERIFIED**.

### Health and readiness

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
Invoke-WebRequest http://127.0.0.1:8000/api/v1/ready
```

Status: **AUTOMATED TEST COVERAGE**; no persistent staging service was
available.

### Logs

```powershell
Get-Content .\results\audit\events.jsonl -Wait
```

Status: **NOT EXECUTED HERE**; the path is the configured audit destination,
not a claim that a staging log exists.

### Restart

Stop the foreground process with `Ctrl+C`, then rerun the start command.

Status: **LOCAL COMPOSE VALIDATION PASS**. Restart and down/up were exercised;
registry identity persisted while process-local runtime history reset as
designed. Host service-manager boot/reboot behavior remains unverified.

## Sensor agent

The following commands are the supported installed-agent command sequence. The
CLI syntax/configuration contracts and a real Windows HTTPS agent run through an
isolated reverse proxy are tested. A public staging sequence is **NOT VERIFIED**.

### Install

```powershell
python -m pip install .\dist\sih26_26153-0.1.0-py3-none-any.whl
sentinel-agent --version
sentinel-agent --help
```

Package build and isolated wheel smoke: **PASS**. The package install path was
validated; no production host install was performed.

### Init

```powershell
sentinel-agent init --server-url https://sentinel.example --interface "Ethernet" --environment production
```

Status: **CLI CONTRACT TESTED; REAL STAGING EXECUTION NOT TESTED**.

### Register

```powershell
sentinel-agent register --enrollment-token <one-time-enrollment-token>
```

Status: **AUTOMATED AGENT/API CONTRACT TESTED; REAL STAGING EXECUTION NOT TESTED**.

### Start and status

```powershell
sentinel-agent config validate
sentinel-agent start
sentinel-agent status
sentinel-agent diagnostics
```

Status: configuration/status/diagnostic contracts are tested. A real Windows
foreground capture run, L=10/K=5 forecast, and graceful stop were exercised in
Phase S.

### Stop and restart

```powershell
sentinel-agent stop
sentinel-agent restart
```

Status: **AUTOMATED LIFECYCLE COVERAGE ONLY**. Windows service/reboot behavior
was not tested and is not claimed.

## Required staging execution

Run the commands above only after an administrator supplies a trusted staging
hostname, certificate/CA, reverse proxy, Docker runtime or host service, and a
real sensor interface. Record actual command output in
[STAGING_VALIDATION_REPORT.md](STAGING_VALIDATION_REPORT.md). Do not use
`verify=False` or `curl -k`.

## Phase Q validation record

On 2026-09-04, the actual CLI registered and started a Wi-Fi sensor through a
real Nginx HTTPS proxy. Central outage buffering/retry/flush, agent offline and
same-identity recovery, Compose registry persistence, and independent customer
traffic were observed. The run did not reach ten contiguous accepted live
states, so L=10/K=5 forecast readiness is **NOT VERIFIED**. Physical
multi-host, expired certificate, TruffleHog, and 30-minute soak evidence are
also **NOT VERIFIED**. Continue to use a trusted CA and never bypass TLS
verification.

## Phase R remote forecast record

On 2026-09-04, the actual agent and real Wi-Fi/Npcap capture ran through the
temporary Nginx TLS proxy. Registration, heartbeat, telemetry delivery, central
outage retry/flush, stale/offline transitions, same-identity restart, and
customer-path isolation passed. The run did not produce ten contiguous accepted
states, so live `L=10` history, `K=5` inference, forecast scores/timestamps,
warning rows, and dashboard forecast-ready state remain **NOT VERIFIED**.

The repeatable monitor-only observer is
[`scripts/phase_r_remote_forecast.py`](../scripts/phase_r_remote_forecast.py).
It must be run with a real viewer token in an environment variable and a trusted
CA; it never posts telemetry. Record future live evidence in
[`PHASE_R_REMOTE_FORECAST_REPORT.md`](PHASE_R_REMOTE_FORECAST_REPORT.md) without
claiming staging or production readiness from local Compose results.

## Phase S and Phase T current record

On 2026-09-04, the actual Windows Wi-Fi/Npcap agent reached ten contiguous
accepted states through the isolated Nginx HTTPS proxy. The existing LSTM
returned five forecast rows, a rolling update was observed, the dashboard
showed the selected sensor as `ONLINE`, `FRESH`, `FORECAST READY`, and `10 / 10`,
and `sentinel-agent stop` terminated the foreground process cleanly. The
current release-candidate evidence, including package, browser, Docker,
customer-path, security, and documentation checks, is consolidated in
[`PHASE_T_PUBLIC_RELEASE_CANDIDATE_REPORT.md`](PHASE_T_PUBLIC_RELEASE_CANDIDATE_REPORT.md).
Physical multi-host/five-sensor deployment, 30-minute soak, expired
certificate, public ingress, and TruffleHog remain **NOT VERIFIED**.
