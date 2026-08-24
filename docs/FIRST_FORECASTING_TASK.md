# First Forecasting Task

Date: 2026-08-24

## Initial target

For a sequence ending at row/time `t`, predict the binary attack state at the next row position:

```text
X = [S(t-L+1), ..., S(t)]
Y = binary_attack(t+1)
```

The initial implementation supports `sequence_length`, `stride`, and `forecast_horizon`, with the first experiment using `forecast_horizon = 1`.

`Benign -> 0` and `Infilteration -> 1` are retained as the documented target mapping. The window generator never crosses train/validation/test boundaries and emits origin and target timestamps as metadata.

## Important scope limitation

The current model-safe artifact contains flow rows, not fixed-interval network-state aggregates. The first output is therefore a deterministic flow-row sequence mechanics test. It is not yet the final `S(t)` network-state representation described in the temporal specification.

## Data sufficiency

The real file covers one day, `2018-02-28 01:00:00` through `12:59:59`, with early and late infiltration blocks. This is enough to validate chronological partitioning and future-target alignment, but not enough to claim cross-day or cross-scenario forecasting robustness. A second real infiltration-related day, preferably `2018-03-01` from the same CSE-CIC-IDS2018 source with matched flow/PCAP provenance, is the minimum recommended addition before treating the temporal model as generalizable.
