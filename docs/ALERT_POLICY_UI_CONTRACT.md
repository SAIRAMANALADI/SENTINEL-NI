# Alert Policy UI Contract

The dashboard may consume the following deterministic fields from the frozen K=5 +10-second forecast:

| Field | Required value/meaning |
|---|---|
| `forecast_score` | Raw model output in [0, 1], displayed as **Forecast Score**; not a calibrated probability |
| `operating_mode` | `sensitive`, `balanced`, or `conservative` |
| `threshold` | The threshold for the selected mode from `configs/operating_policy.yaml` |
| `decision_state` | `warning` when `forecast_score >= threshold`; otherwise `no_warning` |
| `decision_label` | **Predictive warning** or **No predictive warning** |
| `forecast_offset_seconds` | `10` |
| `sequence_length` | `10` states |
| `model_version` | Frozen K=5 development checkpoint identifier |

## Exact user-facing wording

- Warning: **Predictive warning** — “The model score crossed the selected threshold for an elevated attack-state forecast at +10 seconds.”
- No warning: **No predictive warning** — “The model score did not cross the selected threshold for an elevated attack-state forecast at +10 seconds.”

Always include the active mode and threshold next to the state. Do not use “attack detected,” “confirmed intrusion,” “confidence,” or MITRE technique language for this score.

## Alert budget display

If an aggregate alert rate is shown, label it **Estimated alerts per minute (10-second state-rate)**. Do not label it incident rate or packet rate. The current policy's values are validation-derived estimates only.

## Missing/invalid input behavior

If the score is missing, non-finite, or outside [0, 1], do not render a warning or no-warning state. Render an input-error state and log the validation failure. A score exactly equal to the threshold is a warning.
