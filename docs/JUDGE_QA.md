# Judge Q&A

## 1. What problem are you solving?

We forecast whether the next network state is likely to contain observed malicious traffic, using recent network-state history rather than waiting only for a current-state classification.

## 2. How is this different from a traditional IDS?

A traditional IDS commonly raises an alert on current observed traffic. This prototype adds a future-state forecast over +10s to +50s. It is complementary, not a replacement for a production IDS.

## 3. Why forecast instead of classify?

Forecasting supports earlier operational attention. The target is explicitly the future attack-state value at the next 10-second state, not only the current state.

## 4. Why use a temporal model?

Network behavior can depend on recent state history. The LSTM consumes 10 ordered states, representing 100 seconds of context, while respecting capture-day boundaries.

## 5. Why LSTM?

LSTM was selected as a controlled, straightforward sequence-model experiment for ordered state data. It is a development model, not a claim that it is universally optimal.

## 6. What does K-step forecasting mean?

K=5 returns five direct future state scores at +10s, +20s, +30s, +40s, and +50s. Each output corresponds to a future binary attack-state value.

## 7. What exactly does the model predict?

`future_attack_state(t) = binary_attack_state(t + 10 seconds)` within the same capture day. A positive means the future state contains at least one flow labeled non-Benign under the approved target rule.

## 8. Why is the score not a calibrated probability?

No approved post-hoc calibration model was fitted. Therefore the UI calls it Forecast Score and does not present it as a calibrated probability.

## 9. How do you explain predictions?

Deterministic masking measures how the model score changes when a feature-position is replaced with the standardized training mean. This reports sensitivity, not causality.

## 10. How do you prevent temporal leakage?

Windows are chronologically ordered, isolated by capture day and split, and targets are read only from future rows. The final test day is not used for model or threshold selection.

## 11. How was the train/test split created?

Complete capture days were used: train 2018-02-14 and 2018-02-21, validation 2018-02-22, and test 2018-02-28. Rows were not randomly mixed across days.

## 12. Why are there only certain capture days?

Those are the locally available approved CSE-CIC-IDS2018 flow days. No eligible additional unseen day was available, so temporal generalization remains limited.

## 13. What are the major limitations?

V1 is flow-derived, has incomplete packet-level enrichment, limited capture-day diversity, distribution shift, raw-score calibration limitations, and no production live-capture path.

## 14. What happens if traffic distribution changes?

Scores and alert behavior may shift. The system should monitor score distributions and validation performance, then require a new approved data/split experiment before changing policy.

## 15. How does the system operate offline?

The CLI and dashboard use local Python packages, local checkpoints, local preprocessing/configuration, and the local sample. They do not call cloud services or external APIs at runtime.

## 16. How would this scale in a real network?

A production design would add a streaming state builder, durable model/policy versioning, monitoring, resource controls, alert deduplication, and a validated deployment process. Those are not implemented in this prototype.

## 17. Why is packet-level enrichment currently limited?

The available flow artifact lacks canonical five-tuple and machine identity fields needed to match it safely to the approximately 53.25 GB PCAP archive. Guessing a match would be scientifically indefensible.

## 18. What is novel about the approach?

The project combines a documented flow-to-state contract, day-aware temporal evaluation, direct multi-horizon future-state forecasting, validation-only operating policy, and offline explanations in one reproducible prototype. Novelty claims require stronger comparative evidence.

## 19. What happens if the model is wrong?

The policy can produce a missed warning or false warning. The UI makes the score, threshold, mode, and limitations visible; it is decision support, not an autonomous response system.

## 20. What is the next production step?

Acquire an identity-preserving packet/flow subset, validate packet matching, add more capture days, evaluate calibration and generalization, and then design a monitored streaming deployment.
