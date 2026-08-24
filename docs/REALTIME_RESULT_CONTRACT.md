# Real-Time Result Contract

For each completed state after the 10-state buffer is full, `RealtimeEngine` returns an `EngineUpdate` containing:

- `status`: `inference_ready`;
- current state `timestamp`;
- `state_index`;
- `processing_ms`;
- the existing inference result with:
  - K=5 Forecast Scores at +10/+20/+30/+40/+50 seconds;
  - `Predictive warning` / `No predictive warning` policy booleans;
  - top contributing features;
  - temporal sensitivity positions;
  - model version, schema version, target version, operating mode, and threshold;
  - detailed timing fields.

Terminology is intentionally limited to the existing contract: **Forecast Score**, **Predictive warning**, and **No predictive warning**. The result never claims “attack detected”, compromise confirmation, or causal attribution.
