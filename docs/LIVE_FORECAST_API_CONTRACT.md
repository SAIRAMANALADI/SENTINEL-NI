# Live Forecast API Contract

## Endpoint

```text
GET /api/v1/live
```

The endpoint is read-only. It does not start or stop capture and does not run
inference. Viewer authorization follows the existing API role contract.

## Response

```json
{
  "telemetry": {
    "mode": "live",
    "interface": "Wi-Fi",
    "status": "LIVE_RUNNING",
    "event_count": 6977,
    "flow_count": 312,
    "last_event_at": "2026-08-25T11:51:03+00:00",
    "freshness": "DATA FRESH",
    "readiness_state": "FORECAST_READY",
    "packet_quality": {
      "packets_seen": 8522,
      "valid_events": 7326,
      "ignored_events": 1196,
      "dropped_events": 0,
      "valid_percentage": 85.96,
      "ignored_percentage": 14.04,
      "ignored_categories": {"non_ip": 1196}
    }
  },
  "state": {
    "valid_state_count": 13,
    "latest_state_timestamp": "2026-08-25T11:51:00+00:00",
    "buffer_size": 10,
    "buffer_required": 10
  },
  "forecast": {
    "status": "READY",
    "stale": false,
    "reference_timestamp": "2026-08-25T11:50:40+00:00",
    "model_version": "LSTM-DEVELOPMENT-V1-direct-multistep-K5",
    "sequence_length": 10,
    "horizons": [
      {"step": 1, "horizon_seconds": 10, "timestamp": "2026-08-25T17:47:40+05:30", "score": 0.0614500903, "warning": false},
      {"step": 2, "horizon_seconds": 20, "timestamp": "2026-08-25T17:47:50+05:30", "score": 0.0607087873, "warning": false},
      {"step": 3, "horizon_seconds": 30, "timestamp": "2026-08-25T17:48:00+05:30", "score": 0.0543951988, "warning": false},
      {"step": 4, "horizon_seconds": 40, "timestamp": "2026-08-25T17:48:10+05:30", "score": 0.0678957626, "warning": false},
      {"step": 5, "horizon_seconds": 50, "timestamp": "2026-08-25T17:48:20+05:30", "score": 0.0670479015, "warning": false}
    ],
    "forecast_scores": [0.0614500903, 0.0607087873, 0.0543951988, 0.0678957626, 0.0670479015],
    "warning_states": [false, false, false, false, false],
    "threshold": 0.19
  },
  "source_priorities": [],
  "mitigation": {
    "simulation_only": true,
    "recommendations": []
  },
  "last_error": null,
  "updated_at": "2026-08-25T11:51:04+00:00"
}
```

`readiness_state` is one of `INITIALIZING`, `CAPTURING`,
`BUILDING_FLOW_HISTORY`, `BUILDING_NETWORK_HISTORY`, `FORECAST_READY`,
`STALE`, `STOPPED`, or `ERROR`. Packet-quality counters are metadata only;
raw packets and payload bytes are never returned or persisted.

The top-level `startup_timing.stages` array reports observed stage timestamps
and elapsed seconds for the current capture session. It includes packet
capture start, first event, first tracked flow, first completed flow, state
generation, state validation, first valid state, 10-state buffer fill, and
first inference when those stages have occurred.

A ready response contains the actual five `horizons` rows with `step`,
`horizon_seconds`, `timestamp`, `score` (Forecast Score), and `warning`.

## Forecast states

When fewer than ten valid states exist:

```text
forecast.status = WAITING_FOR_LIVE_HISTORY
forecast.horizons = []
forecast.forecast_scores = []
```

No score is fabricated. When ten states exist, the store invokes the existing
frozen LSTM K=5 inference path. When capture stops after a forecast exists:

```text
forecast.status = STALE_NOT_LIVE
forecast.stale = true
```

The last result remains visible but is clearly not presented as current live
data. A restart resets the active buffer and exposes the previous result only
as `last_forecast.stale=true` until a new history is ready.

## Source and mitigation

`source_priorities` contains candidate source IPs, priority labels, and
measured reasons. A priority is not attacker attribution. Mitigation output is
recommendation-only and always includes `simulation_only=true`; automatic
blocking is not performed.

## Failure behavior

- unavailable backend: Streamlit displays `BACKEND UNAVAILABLE`;
- stale telemetry: Streamlit displays `DATA STALE`;
- malformed live event: the capture callback remains alive and `last_error` is
  exposed in technical details;
- no live history: waiting status with no forecast rows.
