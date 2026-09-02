# Live Release-Validation Wrapper

The Windows wrapper is [`scripts/run_live_rc_validation.ps1`](../scripts/run_live_rc_validation.ps1). It validates the backend live-capture path only; it does not start or validate the frontend.

## What it starts

By default the wrapper starts the project virtual-environment Python executable with Uvicorn and the existing `src.api.app:app` application. It binds to loopback (`127.0.0.1`) and uses the selected telemetry interface. Customer application traffic is not routed through this process.

Example:

```powershell
& .\scripts\run_live_rc_validation.ps1 -Interface "Wi-Fi"
```

The release-candidate duration must be at least 300 seconds. The default configured duration is 330 seconds; the measured runtime can be longer because each capture iteration includes API requests, best-effort traffic generation, and a five-second interval.

## Startup contract

The wrapper does not treat a process or open port as readiness. Its bounded sequence is:

```text
preflight port
  -> start owned process
  -> confirm owned PID remains alive
  -> poll /api/v1/health
  -> poll /api/v1/ready
  -> start telemetry
  -> run live validation
```

Health must return the expected `ok`/`HEALTHY` service response. Readiness must return HTTP 200 with `ready=true`.

Default timing controls:

| Control | Default |
|---|---:|
| Total startup timeout | 60 seconds |
| Health request timeout | 2 seconds |
| Readiness request timeout | 5 seconds |
| Live request timeout | 15 seconds |
| Control request timeout | 20 seconds |
| Poll interval | 500 milliseconds |

The startup deadline is shared by the health/readiness probes. The live request timeout is separate because `/api/v1/live` includes current runtime state and forecast information.

## Port and stale-process behavior

The default port is `8005` for this validation wrapper and the bind address is configurable with `-BindAddress`. Before starting a server, the wrapper rejects an existing listener instead of treating its response as proof that the newly launched process started. Use `-UseExistingServer` only after independently verifying that the listener is the intended Sentinel instance.

The wrapper does not infer backend availability from the frontend port.

## Logs and cleanup

Spawned stdout and stderr are redirected to unique temporary files so a long-running process cannot deadlock on unconsumed pipes. If startup fails, the wrapper reports:

- command, bind address, and port;
- elapsed time;
- last health and readiness probe result;
- owned process ID and exit code;
- redacted tails of stdout/stderr.

Temporary logs are removed at the end of the run. A spawned process is stopped by its captured PID in `finally`; an existing server is never stopped by the wrapper.

## Platform limitations

This validation script is Windows-oriented. It uses the project `.venv\Scripts\python.exe`, `Get-NetTCPConnection`, `Start-Process`, and Windows process cleanup. Real local packet capture additionally requires an available Npcap/libpcap-compatible backend and a valid interface name. Docker, TLS, reverse proxy, and multi-host deployment must be validated separately.

## Troubleshooting

- `Port ... is already listening`: inspect the reported PID and stop the intended service, or use `-UseExistingServer` only for a verified Sentinel process.
- `process_exited_before_readiness`: inspect the reported stderr tail; common causes include an invalid environment/configuration or a bind conflict.
- `startup_or_readiness_timeout`: confirm the selected port/bind address and inspect the last health/readiness results and log tails.
- `FORECAST_READY` is not immediate: the live runtime must build the required `L=10` history from valid captured events.
- `LIVE_STOPPED` after completion is expected; the wrapper stops telemetry and its owned server during cleanup.
