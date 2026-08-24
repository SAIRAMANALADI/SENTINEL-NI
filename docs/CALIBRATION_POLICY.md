# Calibration Policy

## V1 decision

The LSTM outputs are **not treated as calibrated probabilities** in Version 1. The dashboard and reports must call the value **Forecast Score**, not “probability,” “confidence,” or “risk percentage.”

The current score diagnostics are evidence about calibration quality, not a license to apply a transform. Existing validation diagnostics recorded Brier score 0.041466 and ECE 0.033177 for the K=5 +10-second output. The final-test diagnostics are descriptive only and were not used to define this policy.

## No calibration transform in V1

No Platt scaling, isotonic regression, temperature scaling, beta calibration, or other post-hoc transform is applied. Thresholds operate directly on the frozen model score.

## Future calibration procedure

If probability-like values become a product requirement, a separate approved experiment must:

1. fit the calibrator using training data, or a declared calibration partition derived before evaluation;
2. select any calibration hyperparameters on validation data only;
3. freeze the calibrator and its parameters;
4. evaluate once on the final test day after all policy decisions are frozen;
5. report reliability diagrams, Brier score, ECE, calibration sample counts, and the prevalence shift between calibration and evaluation data.

The final test day must never be used to fit or tune the calibrator.

## UI contract

Use `Forecast Score` as the numeric field. Use `Predictive warning` or `No predictive warning` for the thresholded state. See `docs/ALERT_POLICY_UI_CONTRACT.md` and `configs/operating_policy.yaml`.
