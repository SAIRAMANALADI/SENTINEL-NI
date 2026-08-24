# Developer 1 — ML / WORLD MODEL

## Mission
Build the forecasting intelligence.

## Deliverables
1. deterministic preprocessing
2. temporal window builder
3. Logistic Regression baseline
4. LSTM/GRU world model
5. K-step forecasting
6. evaluation report
7. inference module
8. saved model artifact

## Work Order

### Task 1 — Preprocessing
Build a deterministic pipeline:
- numeric conversion
- missing-value handling
- encoding
- scaling/normalization
- reusable preprocessing artifact

### Task 2 — Temporal Windows
Implement:
```text
S(t-n) ... S(t)
        ↓
predict S(t+1 ... t+K)
```
Use temporal/scenario-aware splitting.

### Task 3 — Logistic Regression
Save:
- precision
- recall
- F1
- false-positive rate
- confusion matrix
- inference time where practical

### Task 4 — LSTM/GRU
Start simple:
- sequence input
- hidden layers
- dropout
- output head
- deterministic seed
- checkpointing

### Task 5 — K-step Forecast
Start with K=3.
Return a structured inference result, e.g.:
```python
{
  "current_state": ...,
  "forecast": [
    {"step": 1, "probability": ...},
    {"step": 2, "probability": ...},
    {"step": 3, "probability": ...}
  ]
}
```

### Task 6 — Explainability
Use SHAP where practical, otherwise robust feature ablation/importance.
Never fabricate explanations.

### Task 7 — Evaluation
Check:
- class imbalance
- leakage
- scenario separation
- calibration
- early-warning lead time

Outputs:
- `results/ml_baseline_vs_world_model.json`
- `results/ml_report.md`

## Codex rule
Give Codex one bounded task at a time. Tell it to read existing code, preserve interfaces, add tests, and avoid unrelated dependencies.

## Done when
- train command works
- inference command works
- model/preprocessor reload correctly
- metrics reproduce from a clean run
- leakage audit passes
