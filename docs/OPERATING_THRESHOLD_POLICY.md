# Operating Threshold Policy

## Scope

This policy governs the presentation of the frozen Version 1 LSTM development score. It does not retrain a model, change the frozen network-state data, change the target, or change the day-aware split.

## Primary demo forecast

The primary demo output is the first output of the existing direct K=5 checkpoint:

- model checkpoint: `models/lstm_multistep_k5.pt`
- historical context: L=10 states
- displayed forecast: +10 seconds
- source target semantics: the approved `future_attack_state(t)` definition

This is a development/demo operating choice. It is not a claim that K=5 is the final architecture winner. The +20s through +50s outputs remain available as supplementary multi-step outputs but are not used for this primary threshold policy.

## Selection rules

Thresholds were swept on the validation split only from 0.05 through 0.95 in 0.01 increments. The final test day was not loaded or used to select a threshold, operating mode, calibration, or alert policy.

- Sensitive: maximize validation recall subject to validation FPR <= 0.25.
- Balanced: minimize the absolute validation precision/recall gap subject to validation FPR <= 0.10 and non-zero recall; fall back to any non-zero-recall point if the constraint has no candidate.
- Conservative: minimize validation FPR subject to non-zero recall.

These rules make the operational trade-off explicit. No threshold is selected by F1 alone.

## Alert budget interpretation

An alert is one validation state whose score is greater than or equal to the selected threshold. `alerts_per_minute` is estimated as:

`alert_count / validation_state_count * 60 / 10`

because each state represents a 10-second interval. It is a state-rate estimate, not a claim about unique incidents, continuous traffic, or deduplicated alerts.

The complete 0.05–0.95 sweep is in `results/THRESHOLD_POLICY_SWEEP.csv`; the selected points are summarized in `results/OPERATING_MODES.md`.

## Decision semantics

At or above the selected threshold, the UI shows **Predictive warning**. Below the threshold, it shows **No predictive warning**. The warning means that the model score for an elevated attack-state forecast at +10 seconds crossed the configured operating threshold. It does not mean an attack was detected, confirmed, attributed, or mapped to MITRE.

## Primary mode

**Balanced** is the primary demo mode. It is the least misleading default among the three explicitly labeled modes because it meets the predeclared validation FPR constraint without presenting the high-alert Sensitive point as a normal default. Its limitations remain visible in the final policy report.

## Frozen-data guardrail

The policy layer reads the existing validation split and frozen K=5 checkpoint. It does not alter `data/raw/`, `data/processed/`, the feature pipeline, the target specification, the model checkpoint, or the final test day.
