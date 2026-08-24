# Temporal Forecasting Specification

## Status

Design specification only. No hyperparameters, target definition, or model has been finalized, and no training is authorized by this document.

## 1. Network state definition

One network state `S(t)` is a feature vector summarizing traffic observed during a fixed interval ending at forecast origin `t`. The MVP state should be aggregated at a documented scope, initially considered as:

- whole selected scenario/network;
- source-host or destination-host group; or
- source/destination pair group.

The scope is an experiment. It must be chosen only after checking the selected dataset’s topology and labels. A state must include the interval start/end, scenario identity as metadata, row/flow counts, numeric traffic statistics, and target provenance. Scenario identity is not a model feature by default.

## 2. Traffic aggregation

For candidate interval width `W`, assign a flow or packet event to the interval containing its authoritative start timestamp. Compute only information available at or before the interval end. Candidate aggregations include counts, bytes, packets, rates, durations, protocol proportions, port diversity, endpoint fan-out, directional ratios, and packet-statistic summaries when source data supports them.

Incomplete flows, timezone inconsistencies, out-of-order events, and events spanning interval boundaries require an explicit policy and audit record.

## 3. Candidate window-size experiments

These are experiment candidates, not final hyperparameters:

| Experiment dimension | Candidate values | Selection evidence |
| --- | --- | --- |
| Aggregation width `W` | 1 s, 10 s, 60 s, 5 min, 15 min | Label alignment, sample count, warning lead time, stability |
| History length `L` | 3, 6, 12, 24 states | Validation performance and minimum history availability |
| Forecast horizon `K` | 1, 3, 5 states | Official PS, operational usefulness, calibration |
| Entity scope | Network, host group, endpoint pair | Leakage review and data sufficiency |

The current YAML `forecast_horizon_k: 3` is a placeholder only.

## 4. Historical sequence

Given ordered states, the model input at origin `t` is:

```text
[S(t-L+1), ..., S(t)]
```

The window builder must emit the source scenario, interval boundaries, input-state identifiers, target-state identifiers, and split assignment. Windows are created only after split boundaries or guard gaps are established.

## 5. Prediction target

The primary candidate target is a future attack-state indicator for each horizon step:

```text
y(t+h) = 1 if the audited target rule says an attack is present in the future interval
         0 otherwise
```

Alternative experiments may predict attack intensity, label distribution, or a structured future state. The target rule must specify whether “any attack,” attack proportion, or a particular class triggers `1`. The official PS may require a different target; until then the target is UNKNOWN and provisional.

## 6. K-step representation

The structured output is a list indexed by horizon:

```python
{
    "origin": "timestamp or interval identifier",
    "forecast": [
        {"step": 1, "target_interval": "...", "probability": 0.0},
        {"step": 2, "target_interval": "...", "probability": 0.0},
    ],
}
```

Direct multi-output and recursive one-step forecasting are experiments. The implementation must record which strategy was used and must not imply that probabilities are calibrated until calibration is tested.

## 7. Future attack probability

For a binary target, the probability at step `h` is intended to represent:

```text
P(y(t+h) = 1 | S(t-L+1), ..., S(t))
```

It must be produced by a fitted model or baseline and evaluated on a time/scenario-separated holdout. Thresholded alerts are separate from probabilities. Calibration, class imbalance, false-positive burden, and confidence/uncertainty reporting require experiments.

## 8. Early-warning definition

An alert qualifies as an early warning only if:

1. the forecast origin precedes the first confirmed positive target interval;
2. the alert is emitted at least one complete prediction interval before that interval, unless the PS defines another lead time;
3. the alert is counted with its threshold, horizon, and false-positive context; and
4. the target label was not used to construct the current state.

Lead time, false alarms, missed attacks, and alert persistence must be reported together.

## 9. Temporal splitting

Preferred order:

1. Hold out complete scenarios when multiple scenarios exist.
2. Within the development scenarios, order by time and use earlier time for training and later time for validation.
3. Keep a guard gap at least as large as the maximum feature/sequence dependency where justified.
4. Construct windows without allowing source rows or future intervals to cross partitions.
5. Use the final untouched scenario or final chronological block only once for final evaluation.

If only one short scenario is available, report that the result is within-scenario temporal validation and not cross-scenario generalization. Random row splitting is prohibited for this forecasting design.
