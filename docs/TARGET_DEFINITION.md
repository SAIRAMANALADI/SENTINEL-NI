# Baseline Target Definition

Date: 2026-08-24

## Binary target

The first baseline uses the verified source-label mapping:

```text
Benign        -> 0
Infilteration -> 1
```

The original `Label` and `original_label` remain outside `X` in the clean sidecar. The model-safe feature artifact contains neither target column. The training script joins the target and timestamp sidecar by the deterministic row order produced by Developer 2’s clean/model artifacts, then verifies equal row counts.

## Why binary first

The binary target is the smallest measurable baseline for current-state classification:

```text
X_t -> P(attack_t)
```

It supports class-weighted Logistic Regression and precision/recall-oriented evaluation without prematurely inventing attack stages or MITRE mappings.

## Limitations

- `Infilteration` is the dataset’s original label spelling and is preserved exactly.
- The binary target collapses attack behavior into one positive class and does not distinguish stages, techniques, severity, or future state.
- The target is a current-state label for the baseline, not a future attack forecast.
- The source labels are flow-level and the current slice covers one capture day; cross-day and cross-scenario generalization are not measured.
- The target must not be used to construct current-state features or preprocessing statistics.

## Relationship to future forecasting

The first temporal experiment shifts the same binary state one horizon forward:

```text
[S(t-L+1), ..., S(t)] -> binary_attack(t+1)
```

This is a mechanics and feasibility test, not the final world model or a claim that the single-day slice supports robust early warning.
