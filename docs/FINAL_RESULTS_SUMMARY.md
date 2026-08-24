# Final Results Summary

All metrics below are measured results from the recorded artifacts. Baseline and LSTM tables use the final held-out test partition after validation-only selection. The multistep thresholds were frozen before that test evaluation. These scores are not calibrated probabilities.

## Baseline

Logistic Regression, final held-out test at the recorded threshold 0.40:

| F1 | PR-AUC | ROC-AUC | FPR |
|---:|---:|---:|---:|
| 0.121721 | 0.250304 | 0.542768 | 0.027549 |

## LSTM

Direct K=1, final held-out test, +10 seconds:

| F1 | PR-AUC | ROC-AUC |
|---:|---:|---:|
| 0.040816 | 0.287448 | 0.672474 |

Direct K=3, final held-out test:

| Horizon | F1 | PR-AUC | ROC-AUC |
|---:|---:|---:|---:|
| +10s | 0.074576 | 0.267615 | 0.662806 |
| +20s | 0.019656 | 0.262257 | 0.655515 |
| +30s | 0.019608 | 0.266161 | 0.655939 |

Direct K=5, final held-out test:

| Horizon | F1 | PR-AUC | ROC-AUC |
|---:|---:|---:|---:|
| +10s | 0.120401 | 0.322339 | 0.681121 |
| +20s | 0.066587 | 0.327241 | 0.682885 |
| +30s | 0.064286 | 0.327634 | 0.684613 |
| +40s | 0.085947 | 0.323251 | 0.681979 |
| +50s | 0.081301 | 0.319885 | 0.681161 |

These are descriptive held-out results, not a claim that K=5 is a final architecture winner.

## Explainability

Measured top feature sensitivities from the deterministic mean-mask ablation report on the first 512 validation sequences, K=5 +10s:

| Feature | Mean absolute score change |
|---|---:|
| `mean_iat` | 0.07294836 |
| `ack_flow_ratio` | 0.03313598 |
| `fwd_packet_share` | 0.02288171 |
| `syn_flow_ratio` | 0.02035411 |
| `fwd_byte_share` | 0.01075220 |

These values indicate model sensitivity under masking. They do not show that a feature caused an attack.

## Operating policy

- Primary mode: Balanced.
- Threshold: 0.19, loaded from `configs/operating_policy.yaml`.
- Score >= threshold: **Predictive warning**.
- Score < threshold: **No predictive warning**.

## Tests

The latest full repository suite passed **133 tests**. Historical experiment counts in this summary are not current maintenance-suite counts.
