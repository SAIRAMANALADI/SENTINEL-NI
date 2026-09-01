# Model Contract

The serving model is the frozen LSTM K=5 checkpoint used by the V1 data and
state pipeline. It consumes exactly 17 numeric flow-derived network-state
features in the order defined by `configs/state_feature_schema.yaml`.

Serving also validates the 10-state, 10-second, same-day context window and
the compatible preprocessing, policy, and checkpoint metadata. Invalid
feature sets, timestamps, NaN, infinity, cross-day windows, and incompatible
artifacts are rejected.

The model output is named `Forecast Score`. It is not a calibrated
probability. The operating policy maps the score to `Predictive Warning` or
`No Predictive Warning`; the result is not an attack confirmation.

The checkpoint and preprocessor are local deployment artifacts and are
ignored by Git. Operators must obtain approved artifacts through the project
release process and verify their compatibility before exposing the API.
