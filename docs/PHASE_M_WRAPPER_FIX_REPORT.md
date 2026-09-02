# Phase M Wrapper Fix Report

## Scope

Phase M addressed only the live release-validation wrapper startup/health-detection defect. No ML, data, feature, target, model, threshold, source-attribution, or mitigation code was changed.

## 1. Exact original failure

The Phase L wrapper was:

```powershell
& .\scripts\run_live_rc_validation.ps1 -Interface "Wi-Fi" -DurationSeconds 300
```

Its recorded failure was:

```text
Host live API did not start on port 8005
```

The original wrapper polled only `http://127.0.0.1:8005/api/v1/health` for 30 attempts, did not check the launched PID, and did not capture child stdout/stderr. A separate Phase L attempt also saw a `/api/v1/live` request exceed the wrapper’s 10-second request timeout.

## 2. Reproduction and root cause

The original script was rerun before modification. It reached its capture loop when a pre-existing Python process was listening on port 8005. Inspection identified PID `7476`, a prior local Sentinel process. The original wrapper did not reject that listener and did not prove that the process it launched owned the responding service. This is a stale/conflicting-listener false-positive risk and explains why the same command could fail or appear to work depending on leftover process state.

The original failure message was also not actionable because process launch logs and exit code were unavailable. The endpoint paths themselves were correct (`/api/v1/health` and `/api/v1/ready`); the missing readiness check and ownership/diagnostic handling were the wrapper defects.

## 3. Implementation change

Only `scripts/run_live_rc_validation.ps1` was changed:

- added configurable bind address and bounded startup/request timing parameters;
- rejected an existing listener before a new process is launched;
- captured the spawned PID and checked that it remains alive during startup;
- redirected stdout/stderr to unique temporary files;
- polled both `/api/v1/health` and `/api/v1/ready`;
- required health `status=ok`, service state `HEALTHY`, and readiness `ready=true`;
- shared one startup deadline across the probes;
- separated health, readiness, control, and live request timeouts;
- emitted redacted diagnostics on failure;
- stopped only the process owned by the wrapper and removed temporary logs.

## 4. Startup and readiness behavior

The corrected sequence is:

```text
preflight listener check
  -> Start-Process and capture PID
  -> PID-alive check
  -> /api/v1/health
  -> /api/v1/ready
  -> telemetry start
```

An open port, an unrelated process, or health without readiness cannot produce success.

## 5. Timeout policy

Defaults are:

- total startup budget: 60 seconds;
- health probe: 2 seconds;
- readiness probe: 5 seconds;
- live endpoint: 15 seconds;
- control endpoints: 20 seconds;
- polling interval: 500 milliseconds.

The live timeout was raised from 10 to 15 seconds only after the Phase L local observation measured p95 `/api/v1/live` latency at `2483.79 ms`. It remains bounded and separate from startup. No unbounded wait was introduced.

## 6. Cleanup behavior

On success or failure, telemetry is stopped when this wrapper started it. If the wrapper started the server, only its captured process ID is stopped. `-UseExistingServer` never stops the existing process. Temporary diagnostic logs are deleted after the diagnostics have been emitted.

## 7. Platform considerations

The wrapper is Windows-oriented because it uses the project Windows virtual environment, `Start-Process`, `Get-NetTCPConnection`, and Windows process management. It preserves the loopback security default and does not broaden binding. Docker/TLS/reverse-proxy and physical multi-host checks remain separate environment validations.

## 8. Focused tests

Added [`tests/test_live_wrapper.py`](../tests/test_live_wrapper.py), which verifies the wrapper’s health/readiness contract, stale-listener/PID handling, redacted diagnostics/log capture, cleanup hooks, and separate live timeout. Result:

```text
4 passed in 0.05s
```

A controlled one-second startup-budget run returned the expected failure category and left no listener on its test port.

## 9. Full regression

After the fix:

- full pytest: **PASS — 285 passed, 2 warnings**;
- focused wrapper tests: **PASS — 4 passed**;
- frontend typecheck/build: **PASS**;
- wheel/sdist build: **PASS**;
- pip check: **PASS — No broken requirements found**;
- strict release audit: **PASS**;
- PowerShell wrapper parse: **PASS**;
- Compose config: **PASS**;
- `git diff --check`: **PASS** (only existing LF/CRLF conversion warnings);
- protected ML/data diff: **EMPTY — 0 protected files changed**.

The two pytest warnings are existing dependency deprecation warnings from
`websockets.legacy` and Uvicorn’s legacy WebSocket protocol import; no test
failed.

## 10. Local capture regression

Corrected wrapper command:

```powershell
& .\scripts\run_live_rc_validation.ps1 -Interface "Wi-Fi" -Port 8013
```

Result: **PASS**, process exit `0`.

Observed wrapper output:

| Measure | Value |
|---|---:|
| Measured duration | `444.01 s` |
| Interface | `Wi-Fi` |
| Packets seen | `5,935` |
| Completed flows | `364` |
| Valid states | `23` |
| Forecast updates | `14` |
| Final readiness | `FORECAST_READY` |
| Final forecast status | `READY` |
| Dropped events | `0` |
| Ignored events | `410` |
| Live API mean | `613.877 ms` |
| Live API p95 | `3535.229 ms` |
| Stop status | `LIVE_STOPPED` |
| Restart buffer | `0` |
| Restart forecast status | `WAITING_FOR_LIVE_HISTORY` |

After completion, port `8013` had no listening process. The wrapper therefore exercised capture, flow, state, telemetry, forecast readiness, stop, restart-history reset, and cleanup through the actual wrapper path.

## 11. Before/after result

| Check | Phase L baseline | Phase M |
|---|---|---|
| Spawned-process startup | FAIL / coarse startup error | PASS on fresh port |
| Health-only detection | Present | Replaced with health + readiness |
| Stale listener protection | Absent | Present |
| Startup diagnostics | No child logs/PID context | Redacted stdout/stderr, PID, exit code, probe state |
| Live request timeout | 10 seconds; one timeout observed | 15-second bounded timeout |
| Owned-process cleanup | Basic finally cleanup | PID-scoped cleanup plus temporary log cleanup |
| Real local wrapper run | Not reliable | PASS, exit 0 |

## 12. Remaining environment blockers

Phase M did not change the valid Phase L limitations:

- Docker daemon/runtime unavailable;
- real staging TLS and reverse proxy unavailable;
- no second physical host for multi-host validation;
- 30-minute and five-sensor soak not completed;
- browser validation with real sensors not completed;
- production CPU/RAM/leak behavior remains unverified.

## Readiness classification

**OPEN-SOURCE RELEASE READY WITH ENVIRONMENT VALIDATION PENDING**

Fixing the local wrapper does not establish Docker, TLS, multi-host, or production readiness.
