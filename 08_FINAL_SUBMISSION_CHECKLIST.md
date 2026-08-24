# FINAL SUBMISSION CHECKLIST

## Functional
- [ ] CSV ingestion
- [ ] PCAP path if included
- [ ] deterministic preprocessing
- [ ] temporal windows
- [ ] Logistic Regression baseline
- [ ] temporal model
- [ ] K-step forecasting
- [ ] attack-stage prediction
- [ ] explainability
- [ ] offline UI
- [ ] saved model loads
- [ ] deterministic demo works

## Technical
- [ ] no data leakage
- [ ] evaluation methodology documented
- [ ] metrics reproducible
- [ ] assumptions documented
- [ ] limitations documented
- [ ] dataset source recorded
- [ ] model version recorded
- [ ] no secrets committed

## Presentation
- [ ] 5-slide deck
- [ ] architecture diagram
- [ ] PS alignment
- [ ] results table
- [ ] working demo
- [ ] 2-minute demo video
- [ ] README
- [ ] setup instructions
- [ ] clean repository
- [ ] final architecture document

## Judge Questions to Prepare

### Why is this not a normal IDS?
Because it forecasts future network-state evolution and attack progression rather than only classifying current traffic.

### Why start with LSTM?
It provides a practical temporal model that can be implemented, tested and explained under the time constraint. More complex architectures are extensions.

### How do you avoid leakage?
Temporal/scenario-aware splitting plus explicit leakage audit.

### How do you explain predictions?
Feature attribution/ablation plus evidence-linked attack-stage mapping.

### Can it work offline?
Yes. Core inference and dashboard run locally using saved model and preprocessing artifacts.

### Can it scale?
The pipeline is modular: extraction, temporal modeling, inference and UI can scale independently.
