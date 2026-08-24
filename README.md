# SIH26-26153 Foundation

Welcome team.

This repository is the engineering foundation for SIH26-26153, **AI Based Network Attack Forecasting from Network Traffic Data**.

The intended system will ingest network traffic, convert it into a canonical feature table, construct temporal windows, forecast future network state and attack risk, map the result to an operational attack stage, and expose the result through an offline demo. This repository currently contains the foundation and interface contracts only.

## Current status

Foundation scaffold in progress:

- repository structure created;
- provisional data, architecture, leakage, and requirement contracts documented;
- lightweight configuration and package placeholders created;
- smoke and project-structure tests provided;
- no dataset, trained model, metrics, dashboard, or official SIH problem statement has been added yet.

Fields and requirements that depend on the selected dataset or official SIH statement remain explicitly provisional. No results should be treated as valid until the data contract, labels, split policy, and evaluation protocol are approved.

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
app/        future offline dashboard
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
