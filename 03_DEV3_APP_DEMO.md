# Developer 3 — PRODUCT / DEMO / INTEGRATION

## Mission
Turn the ML system into a clear offline working prototype.

## Deliverables
1. Streamlit dashboard
2. input handling
3. inference integration
4. forecast charts
5. attack-stage panel
6. explainability panel
7. baseline comparison
8. deterministic demo mode
9. README/run instructions

## Dashboard Flow
```text
Upload CSV / select demo sample
        ↓
Validate
        ↓
Preprocess
        ↓
Forecast
        ↓
Results
```

## Required Views

### Input
- upload
- demo sample
- validation summary

### Current State
- current risk
- traffic state
- important active features

### Forecast
Show:
- t+1
- t+2
- t+3
- optional extended horizon

### Attack Stage
Show:
- predicted operational stage
- confidence
- supporting evidence

### Explainability
Show:
- top contributing features
- values
- explanation
- uncertainty/caveats

### Baseline
Compare:
- Logistic Regression
- temporal model
- actual metrics

## Architecture Rule
The UI must not contain ML training logic.
Use a clean inference module such as:
`src/forecasting/inference.py`

## Demo Mode
Create a deterministic sample so judges can always see the complete workflow:
1. load sample
2. show current state
3. run forecast
4. display increasing/decreasing forecast
5. show predicted stage
6. show explanation
7. compare baseline

Do not fake metrics or model outputs.

## Done when
A new user can install dependencies, run one command, load the demo input and understand the output without reading the source.
