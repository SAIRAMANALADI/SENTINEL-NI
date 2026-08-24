# SIH26-26153 Foundation

Welcome team.

This repository is the engineering foundation for SIH26-26153, **AI Based Network Attack Forecasting from Network Traffic Data**.

The implemented prototype ingests CSE-CIC-IDS2018 flow data, constructs 10-second network states, builds day-aware temporal windows, forecasts future observed attack-state behavior, applies a validation-selected operating policy, and exposes the result through an offline CLI and Streamlit demo.

## Current status

Current verified state:

- CSE-CIC-IDS2018 four-day flow artifacts are locally acquired but excluded from Git;
- 16,127 fixed 10-second network states with 17 flow-derived model features are available;
- the approved target is `future_attack_state(t) = binary_attack_state(t + 10 seconds)` within the same `capture_day`;
- train/validation/test days are 14-Feb + 21-Feb / 22-Feb / 28-Feb;
- the frozen K=5 LSTM development checkpoint, preprocessing artifact, operating policy, CLI, and offline Streamlit dashboard are implemented;
- packet-level PCAP enrichment remains blocked and is not fabricated.

The authoritative current contracts are [docs/NETWORK_STATE_SPEC.md](docs/NETWORK_STATE_SPEC.md), [docs/TARGET_STATE_SPEC.md](docs/TARGET_STATE_SPEC.md), [docs/WORLD_MODEL_SPEC.md](docs/WORLD_MODEL_SPEC.md), and [docs/INFERENCE_CONTRACT.md](docs/INFERENCE_CONTRACT.md).

## Architecture

```text
Traffic input -> ingestion -> feature extraction -> canonical schema
              -> temporal windows -> baseline model -> temporal model
              -> K-step forecasting -> attack-stage mapping
              -> explainability -> offline dashboard
```

The training and inference paths are separated in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). The interface between network feature engineering and ML is defined in [docs/DATA_CONTRACT.md](docs/DATA_CONTRACT.md).

## Team ownership

| Developer | Ownership |
| --- | --- |
| Developer 1 | ML, preprocessing, temporal windows, models, forecasting, evaluation |
| Developer 2 | Ingestion, flow and packet features, canonical schema, labels, MITRE evidence |
| Developer 3 | Offline dashboard, inference integration, visualization, demo packaging |
| Developer 4 | QA, reproducibility, leakage and data audits, integration, documentation |

## Repository layout

```text
data/       raw, processed, and small sample-data locations
src/        ingestion, features, preprocessing, models, forecasting, MITRE, explainability
app/        offline Streamlit dashboard
configs/    versioned project configuration
tests/      automated tests
notebooks/  exploratory work kept separate from production code
models/     local model artifacts; checkpoints are ignored by Git
results/    generated metrics and reports; generated artifacts are ignored
docs/       contracts, decisions, audits, and runbooks
scripts/    reproducibility and maintenance scripts
```

## Development rules

1. Keep one bounded task per branch or pull request.
2. Treat the canonical data contract as a shared API; document interface changes.
3. Do not commit raw or large datasets, secrets, checkpoints, or generated caches.
4. Keep training separate from inference and use temporal/scenario-aware validation.
5. Do not invent SIH requirements, attack chronology, metrics, or explanations.
6. Do not start Transformer/GNN work before the baseline and first temporal model are working.
7. Every new module must have focused tests and a reproducible command.

## Foundation checks

From this directory:

```bash
python scripts/smoke_test.py
python -m pytest tests/test_project_structure.py
```

Install the lightweight foundation dependencies with:

```bash
python -m pip install -r requirements.txt
```

See [docs/PS_REQUIREMENT_MATRIX.md](docs/PS_REQUIREMENT_MATRIX.md) for requirement traceability and [docs/DECISIONS.md](docs/DECISIONS.md) for provisional architectural decisions.

## What the Prototype Does

The system observes recent network-state history and forecasts future attack-state behavior over multiple horizons. It uses 10-second states, a frozen K=5 LSTM development checkpoint, a validation-selected operating policy, and deterministic model-sensitivity explanations. The result is an offline Forecast Score and a Predictive warning/No predictive warning state—not an “attack detected” verdict.

## Demo

```bash
streamlit run app/streamlit_app.py
```

Use **Run Demo** to execute the deterministic local sample through validation, inference, policy, forecasting, and explanation.

## Run the Demo

Install the project dependencies, then start the offline Streamlit dashboard:

```bash
python -m pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

Use **Run Demo** to execute the deterministic fixture at `data/samples/inference_demo_sequence.csv`, or upload a compatible 10-state sequence containing the approved 17 features, `timestamp`, and `capture_day` columns. The dashboard consumes `predict_network_state_sequence()` from `src/forecasting/inference.py`; it does not train models or implement preprocessing independently.
