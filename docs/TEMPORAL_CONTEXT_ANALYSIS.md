# Temporal Context Analysis

This analysis uses the controlled LSTM-L5/L10/L20 comparison. All runs use the frozen V1 features, target, day-aware split, architecture, optimizer, seed, weighted BCE, and validation-only selection.

## Answers

1. Does longer context improve PR-AUC? **Yes** from L=5 to L=20. Best validation PR-AUC is **0.054243** at L=20.
2. Does longer context improve ROC-AUC? **Yes** from L=5 to L=20. Best validation ROC-AUC is **0.651115** at L=20.
3. Does longer context improve recall? **Yes** from L=5 to L=20. Best validation recall is **0.146341** at L=20.
4. Does longer context improve F1? **Yes** from L=5 to L=20. Best validation F1 is **0.086176** at L=20.
5. Is there evidence of overfitting?
   - L=5: Evidence of overfitting after epoch 4: training loss continued to fall, while validation loss rose and validation PR-AUC fell.
   - L=10: Evidence of overfitting after epoch 1: training loss continued to fall, while validation loss rose and validation PR-AUC fell.
   - L=20: Evidence of overfitting after epoch 1: training loss continued to fall, while validation loss rose and validation PR-AUC fell.
6. Does performance deteriorate as sequence length increases? **Not uniformly**. The metric-by-metric results show whether any gain is consistent across early-warning metrics.
7. Which sequence length should become LSTM-V2? **NO CLEAR WINNER**.
8. Is the improvement large enough to justify moving forward? **No automatic promotion is justified by this comparison alone**. The decision must consider PR-AUC, recall, F1, and FPR together rather than ROC-AUC alone.

## Baseline context

Logistic Regression test reference: F1 `0.121721`, PR-AUC `0.250304`, recall `0.072682`, FPR `0.027549`.

The comparison is an early-warning benchmark, not deployment evidence. The target remains next 10-second malicious-state presence, and the V1 data remains flow-derived with limited temporal/scenario diversity.
