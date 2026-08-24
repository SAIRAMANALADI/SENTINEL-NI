# SIH26-26153 — MASTER EXECUTION PLAN

## Goal
Build a complete offline working prototype for SIH26-26153:
**AI-based Network Attack Forecasting from Network Traffic Data**

Core prototype:
- CSV/PCAP ingestion
- flow + packet-level features
- temporal network-state representation
- multi-step future-state forecasting
- attack/infiltration probability
- predicted operational attack stage
- explainability
- Logistic Regression baseline
- reproducible offline execution
- working demo UI

## Team

### Developer 1 — ML / World Model
Owns:
- preprocessing and temporal windows
- Logistic Regression baseline
- LSTM/GRU temporal model
- K-step forecasting
- evaluation
- saved model/inference interface

### Developer 2 — Network / Feature Engineering
Owns:
- CSV/PCAP ingestion
- flow aggregation
- packet-level features
- canonical feature schema
- labels/state construction
- MITRE mapping support

### Developer 3 — Product / Demo / Integration
Owns:
- Streamlit dashboard
- inference integration
- forecast charts
- attack-stage display
- explainability display
- demo workflow
- README/submission packaging

### Developer 4 — Backup / QA / Research
This developer is a real owner, not spare capacity.
Owns:
- reproducibility
- data sanity checks
- leakage audit
- evaluation verification
- MITRE mapping review
- integration testing
- documentation
- bug triage
- backup implementation when another developer is blocked
- final demo rehearsal

## Repository Rules
Branches:
- main
- dev/ml
- dev/network
- dev/app
- dev/qa

Rules:
1. One feature/task per branch.
2. Never commit large raw datasets.
3. Commit only tiny sample data plus acquisition instructions.
4. Every module gets tests.
5. No silent changes to the canonical feature schema.
6. No random row split for temporal data.
7. Every experiment writes metrics to `results/`.
8. Keep training separate from inference.
9. Final demo must run on a clean machine.

## Recommended Structure
```text
sih26153/
├── data/raw/
├── data/processed/
├── data/samples/
├── src/ingestion/
├── src/features/
├── src/preprocessing/
├── src/models/
├── src/forecasting/
├── src/mitre/
├── src/explainability/
├── app/
├── configs/
├── tests/
├── notebooks/
├── models/
├── results/
├── docs/
├── scripts/
├── requirements.txt
└── README.md
```

## Canonical Feature Contract
Finalize one shared schema covering, as applicable:
- timestamp
- src_ip / dst_ip
- src_port / dst_port
- protocol
- TCP flags
- bytes
- packets
- duration
- inter-arrival statistics
- bidirectional statistics
- TTL statistics
- TCP window statistics
- fragmentation
- payload-size statistics
- retransmission indicators
- fan-out / port-diversity behavior

Exact fields must follow the selected dataset and SIH requirements.

## Model Order
1. Logistic Regression baseline
2. LSTM/GRU temporal model
3. K-step forecasting
4. Explainability
5. Optional graph-derived features
6. Optional Transformer/GNN only after the MVP works

## Milestones
- M1: raw data -> canonical features
- M2: baseline alive
- M3: temporal model alive
- M4: K-step forecast + stage + explanation
- M5: working dashboard
- M6: clean-machine validation + submission package

## Definition of Done
- offline inference works
- CSV input works
- PCAP path works if included in final scope
- temporal forecasting works
- baseline exists
- metrics are reproducible
- attack-stage mapping works
- explanation is shown
- UI works
- README works from a fresh setup
- video/slides/document are ready
