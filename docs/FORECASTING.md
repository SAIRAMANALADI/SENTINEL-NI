# Forecasting

The live runtime rolls a bounded history of ten valid network states. Each
state represents one exact 10-second interval. Once the buffer is full, every
new valid state advances the window and triggers the existing K=5 inference
path for +10, +20, +30, +40, and +50 seconds.

The backend, not the browser, performs inference. A live snapshot exposes the
reference timestamp, forecast timestamps, scores, warnings, threshold,
model/schema/policy versions, and the runtime `session_id`.

When telemetry is stopped or stale, the API marks the forecast accordingly.
It never combines a stopped status with a current-live claim and never
fabricates missing states or targets.
