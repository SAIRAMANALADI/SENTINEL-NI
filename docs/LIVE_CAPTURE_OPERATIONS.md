# Live Capture Operations

## Safe startup

1. Keep `SIH_TELEMETRY_MODE` at `replay` or `mock` unless live capture is
   explicitly approved for the host.
2. Run `python scripts/list_capture_interfaces.py --json`.
3. Select an exact interface name; do not guess from `Ethernet`, `Wi-Fi`, or
   Linux defaults.
4. Set `SIH_TELEMETRY_MODE=live` and `SIH_TELEMETRY_INTERFACE=<exact name>`.
5. Start through the operator-only dashboard button or
   `POST /api/v1/telemetry/start`.
6. Watch `GET /api/v1/telemetry` for status, freshness, counters, and errors.

## Safe stop

Use the dashboard stop control or `POST /api/v1/telemetry/stop`. A stop is
also attempted by the local smoke test in its cleanup path.

## State meanings

`LIVE_RUNNING` means the capture adapter was started. `DATA_STALE` means no
event has arrived within the configured freshness window. `LIVE_ERROR` and
`LIVE_PERMISSION_DENIED` require operator remediation. No forecast is created
from missing telemetry.

## Current limitation

The live adapter and source activity path are operationally separate from the
frozen model-state path. The current packet event contract does not include the
flow-level fields needed to reproduce all 17 frozen state features. The system
must not interpolate or invent those fields.
