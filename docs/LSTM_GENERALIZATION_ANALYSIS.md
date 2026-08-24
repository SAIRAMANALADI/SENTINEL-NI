# LSTM Generalization Analysis

## Status: BLOCKED

The requested unseen-day analysis cannot be performed from the current frozen dataset. It contains no capture day outside the approved train days, approved validation day, and reserved final test day.

1. Which sequence length generalizes best? **Cannot determine; no eligible generalization day was available.**
2. Does the winner remain good under a different day distribution? **Not tested.**
3. Does higher validation performance transfer? **Not testable without another day.**
4. Does FPR become unacceptable? **No generalization FPR exists; no claim is made.**
5. Is temporal context stable across days? **Unresolved.**
6. Is there evidence that the model is learning day-specific behavior? **Cannot establish from the current data.**
7. Should we choose L5, L10, L20, or NO CLEAR WINNER? **NO CLEAR WINNER.**

The prior L5/L10/L20 final-test comparison is not reused for model selection here. In particular, 2018-02-28 remains reserved and untouched for this experiment.

## Next action

Add one independently acquired processed capture day, preserve the current split assignments, and rerun the same L5/L10/L20 configuration with checkpoint and threshold decisions made only on 2018-02-22 validation data.
