# Remote Forecast Validation Record

Validation date: 2026-09-04  
Harness: `scripts/phase_r_remote_forecast.py` (monitor-only; it does not post
telemetry or mutate runtime state)

## Environment

The actual `sentinel-agent` package ran against the central Compose backend
through a real Nginx TLS proxy. The agent used the Wi-Fi interface with
`tls_verify=true`; the temporary CA was supplied explicitly. The capture
backend was Scapy/Npcap.

## Remote sensor attempt

Fresh sensor registration and HTTPS heartbeat passed. Continuous real outbound
HTTPS traffic was generated on the monitored host for approximately 130
seconds. Central accepted real telemetry, but duplicate or gapped 10-second
state timestamps were rejected by the existing contiguous-state contract.

Observed final runtime for the fresh Q/R sensor:

- `state_count=7`
- `history_length=1`
- `history_required=10`
- no forecast update and no five-score forecast payload

No states, scores, or forecast outputs were inserted manually. The LSTM K=5
artifact and the 17-feature/L=10 contract were unchanged.

## Dashboard and multi-sensor result

Compose dashboard/frontend health passed, but a real authenticated
forecast-ready dashboard view was not verified. No second physical host or
five-sensor run was available; isolated processes are not classified as
physical multi-host evidence.

## Recovery result

During a controlled central stop, the actual agent buffered four batches,
retried with backoff, and flushed after the backend restarted. Stopping the
agent caused central OFFLINE/STALE state; restarting the same configuration
preserved the sensor ID and restored heartbeat connectivity.

## Reproduction

Run the real agent first, set the viewer token in the environment named by
`--token-env`, then monitor without writing to the API:

```powershell
$env:SIH_VIEWER_TOKEN = '<viewer-token>'
python scripts/phase_r_remote_forecast.py `
  --base-url https://sentinel.example `
  --sensor-id sensor-<registered-id> `
  --ca C:\path\to\ca.crt `
  --polls 20 `
  --interval 10
```

Credential values must never be committed or included in validation output.
