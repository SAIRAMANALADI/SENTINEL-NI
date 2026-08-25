# Operations Runbook

## Startup

1. Check GET /api/v1/health for process liveness.
2. Check GET /api/v1/ready before sending forecast requests.
3. Confirm telemetry_mode is replay (default) or mock. Use live only after an
   operator has selected an exact interface and installed the platform capture
   dependency.

## Live capture safety

Live capture is disabled unless `SIH_TELEMETRY_MODE=live` and
`SIH_TELEMETRY_INTERFACE` are explicitly configured. Discover interfaces with:

```powershell
python scripts/list_capture_interfaces.py --json
```

Then run the local smoke test for no more than ten seconds:

```powershell
python scripts/live_capture_smoke_test.py --interface "<exact discovered name>" --duration 10
```

The application exposes `/api/v1/telemetry` and operator-only start/stop
controls. Payloads are not stored. The current Docker Compose deployment does
not grant host networking, capture capabilities, or privileged access, so live
capture is not claimed to work inside the container.
4. Start Streamlit only after backend readiness is true.

## Normal operation

- Use POST /api/v1/forecast only with the frozen 10-state/17-feature contract.
- Use POST /api/v1/source-priority for measured candidate-source ranking.
- Use POST /api/v1/mitigation for recommendation-only actions.
- Review JSON logs by request ID and inspect GET /api/v1/metrics periodically.
- Review the JSONL audit path for event and recommendation records; every
  mitigation record must retain simulation_only=true.

## Failure handling

- 503 SERVICE_NOT_READY: inspect /ready checks and reasons; do not return a
  fabricated forecast.
- DATA_STALE or TELEMETRY_UNAVAILABLE: stop forecast consumption until a valid
  adapter is available.
- DEGRADED: source analysis may be unavailable while forecast remains usable;
  show the degraded state to operators.
- 422: fix the request contract; do not bypass validation.
- 401/403: verify configured role token and required permission.

## Shutdown and recovery

Stop the backend process/container gracefully. Audit files are append-only JSONL
and should be retained according to the deployment retention policy. Metrics
are local and reset after restart, so external monitoring is required for
long-running operations.

## Demo mode

The Full Integrated Demo is deterministic demo/test data, not research data or
live telemetry. It produces recommendation-only mitigation and never blocks
traffic.
