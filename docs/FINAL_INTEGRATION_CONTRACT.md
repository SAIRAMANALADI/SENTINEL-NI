# Final Integration Contract

## Status

This contract defines an offline demonstration composition. It does not alter the frozen network-state or ML contracts, does not train a model, and does not claim CSE-CIC-IDS2018 PCAP attribution.

## End-to-end flow

```text
DEMO EVENT
  -> SOURCE ACTIVITY
  -> NETWORK STATE
  -> L=10 HISTORY
  -> EXISTING K=5 INFERENCE
  -> OPERATING POLICY
  -> SOURCE PRIORITY
  -> MITIGATION RECOMMENDATION
```

| Transition | Input | Output | Responsible module | Validation/error behavior |
|---|---|---|---|---|
| Event → source activity | Combined event rows with packet-event fields | Per-source 10-second activity table | `src.streaming.source_activity.aggregate_source_activity` | Required identity/length/flag fields are validated; missing, invalid, negative, or non-finite values raise `ValueError`. |
| Event → network state | Same rows with frozen flow aggregation fields | Exactly one 17-feature state plus timestamp/day per bucket | `src.streaming.state_aggregator.aggregate_flow_window` | Existing required flow columns and numeric source fields are validated; empty/multi-bucket windows raise `ValueError`. |
| State → history | One validated network state | Rolling 10-state sequence | `src.streaming.state_buffer.StateBuffer` | Rejects wrong columns, NaN/Inf, duplicate/out-of-order timestamps, gaps, and cross-day sequences. |
| History → forecast | Exactly 10 frozen states | Existing five K=5 forecast rows and explanation | `src.forecasting.inference.predict_network_state_sequence` | Existing model, preprocessing, schema, checkpoint, and timestamp validation are reused. Errors propagate without fallback scores. |
| Forecast → policy | Existing raw Forecast Scores | Predictive warning / No predictive warning | Existing policy inside `predict_network_state_sequence` | Threshold is loaded from `configs/operating_policy.yaml`; score is not called a probability. |
| Activity + forecast → priority | Source activity table plus existing forecast context | Candidate-source priorities and measured reasons | `src.streaming.source_forecast.prioritize_sources_with_forecast` | Deterministic rule points; no source probability or attacker claim. |
| Priority → mitigation | Priority rows | Recommendation-only actions | `src.evaluation.mitigation_policy.recommendations_for_sources` | Unknown priority raises `ValueError`; automatic blocking remains false. |

## Final result

`src.streaming.final_demo_engine.run_final_demo()` returns one JSON-serializable mapping containing:

- `timestamp`;
- `network_forecast.forecasts` with the actual five model scores;
- `network_status`;
- `source_priorities`;
- `mitigation_recommendations`;
- component and total processing times;
- `simulation_only=true`;
- `pcap_attribution_validated=false`.

## Scientific boundary

The demo event file is explicitly synthetic test data. The real CSE-CIC-IDS2018 flow/state dataset, target, 17-feature schema, L=10 context, K=5 checkpoint, policy threshold, and published metrics are not changed.
