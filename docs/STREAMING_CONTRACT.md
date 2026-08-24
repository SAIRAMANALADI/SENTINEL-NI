# Streaming Contract

## Input event

`ReplayEvent` contains:

- `timestamp`: original naive capture timestamp;
- `capture_day`: ISO date belonging to the timestamp;
- `kind`: `state` or `flow`;
- `payload`: either the exact 17-feature state plus context, or the existing flow fields required by `src.features.network_state`.

The replay source must be chronological. Equal timestamps are allowed for multiple raw flow events; state events must have unique timestamps. Timestamps are never accelerated, rounded, or rewritten in emitted state objects.

## Aggregated state

Each completed state contains exactly these columns, in this order:

```text
17 columns from configs/state_feature_schema.yaml
timestamp
capture_day
```

The state interval is exactly 10 seconds. State arithmetic for raw flow events delegates to `aggregate_network_states()`; no second feature schema exists. Target columns are not streaming model inputs.

## Buffer

`StateBuffer` holds the last 10 validated states. It accepts only same-day states exactly 10 seconds apart.

- duplicate timestamp: hard rejection;
- out-of-order timestamp: hard rejection;
- 5-second/20-second/other gap: `waiting_for_next_valid_state`, with no interpolation;
- capture-day change: buffer reset, with no cross-day sequence;
- NaN/Inf or unsupported columns: hard rejection.

## Inference trigger

The engine emits its first inference update when state 10 is accepted. Every later valid state produces one rolling inference update. The existing `predict_network_state_sequence()` API performs preprocessing, K=5 forecasting, policy application, and explanation.

## Offline replay

Replay is fully local and supports the approved deterministic sample and approved state/flow files. A positive replay speed controls wall-clock sleep only; logical timestamps and forecast timestamps remain the original 10-second timeline.
