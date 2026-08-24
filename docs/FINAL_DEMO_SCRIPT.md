# Final Demo Script

Target duration: **90–120 seconds**.

## Before starting

Run:

```text
python -m streamlit run app/streamlit_app.py
```

Open `http://localhost:8501` or the local URL shown by Streamlit. The deterministic fixture is `data/samples/inference_demo_sequence.csv`.

## 1. Open dashboard — 5 seconds

**Click:** Open the local Streamlit URL.

**Say:** “This is an offline network-state forecasting prototype. It uses a recent sequence of approved 10-second network states.”

**Do not claim:** It is a live packet sensor or a production IDS.

## 2. Run deterministic demo sample — 8 seconds

**Click:** `Run Demo`.

**Point at:** Validation passed, 10 supplied states, and 17 feature columns.

**Say:** “The demo runs the real local sequence through input validation, preprocessing, the frozen K=5 model, operating policy, and explanation.”

## 3. Show current network-state context — 8 seconds

**Point at:** Reference timestamp `2018-02-22T01:01:30`, 10-second interval, 10 input states, and 17 features.

**Say:** “The model sees 100 seconds of recent state context and forecasts the next 50 seconds.”

## 4. Show +10-second forecast — 12 seconds

**Point at:** +10s Forecast Score `0.067844` and threshold `0.19`.

**Say:** “The first forecast score is 0.067844, below the validation-selected Balanced threshold of 0.19, so the state is No predictive warning.”

## 5. Show all forecast horizons — 15 seconds

**Point at:** The five forecast rows:

- +10s: `0.067844`
- +20s: `0.069796`
- +30s: `0.063321`
- +40s: `0.075318`
- +50s: `0.076256`

**Say:** “K-step forecasting gives one direct Forecast Score for each future horizon.”

## 6. Explain score and threshold — 8 seconds

**Point at:** `Forecast Score`, `Balanced`, and `0.19`.

**Say:** “This is a raw Forecast Score, not a calibrated probability. The threshold came from validation data; the final test day was not used for policy selection.”

## 7. Show operating warning — 8 seconds

**Point at:** **NO PREDICTIVE WARNING**.

**Say:** “The policy converts the score into a Predictive warning or No predictive warning state.”

**Do not say:** “Attack detected” or “attack confirmed.”

## 8. Show explanation — 15 seconds

**Point at:** Top contributing signals such as `syn_flow_ratio`, `mean_iat`, and `ack_flow_ratio`, and their temporal positions.

**Say:** “These are the inputs to which this frozen model was most sensitive under deterministic masking. They are not causal explanations.”

**Do not say:** “The model knows the attacker is doing X.”

## 9. Show trajectory — 10 seconds

**Point at:** Forecast Score Trajectory and the horizontal threshold line.

**Say:** “The trajectory makes the score trend across future horizons visible. A rising score is not automatically attack progression.”

## 10. Show technical details — 10 seconds

**Click:** Expand `Technical Details`.

**Point at:** K=5 checkpoint, schema version, target version, Balanced mode, threshold, horizon, timing, and test status.

**Say:** “The complete path is local and reproducible: 104 tests passed, and the UI consumes one stable inference API.”

## Closing sentence

“The prototype forecasts elevated future attack-state behavior from recent network-state history, while keeping the score semantics, validation policy, and limitations explicit.”
