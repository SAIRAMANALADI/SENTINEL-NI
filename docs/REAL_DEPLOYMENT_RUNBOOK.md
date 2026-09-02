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

Status: **AUTOMATED/IN-PROCESS COVERAGE ONLY**. A real foreground staging
start was not run in Phase J.

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

Status: **PROCESS-LEVEL AUTOMATED RESTART CONTRACT ONLY**. Docker/service
restart was not executable because the Docker daemon was unavailable.

## Sensor agent

The following commands are the supported installed-agent command sequence. The
CLI syntax/configuration contracts are tested; the complete real HTTPS staging
sequence is **NOT EXECUTED HERE** because no staging certificate, reverse proxy,
or central staging endpoint exists.

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

Status: configuration/status/diagnostic contracts are tested. A live capture
start and long-running process were not run in Phase J.

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
