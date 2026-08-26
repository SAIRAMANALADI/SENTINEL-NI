# Sentinel / NI

**Predictive network intelligence for security operations.**

Sentinel / NI turns network-flow telemetry into structured 10-second network states, forecasts near-term attack-state behavior, and gives operators a focused warning, source prioritization, mitigation recommendation, and model-sensitivity context.

It is designed around a simple operational question:

> What is the network likely to look like next—and what should the operator look at first?

## Current capabilities

The current verified V1 system provides:

- CSE-CIC-IDS2018 multi-day flow ingestion;
- 16,127 fixed 10-second network states;
- 17 flow-derived model features;
- a frozen K=5 temporal forecasting checkpoint;
- day-aware train, validation, and test boundaries;
- deterministic inference, operating-policy, source-prioritization, mitigation, and explanation outputs;
- a standalone Next.js product interface and a Streamlit fallback/demo interface.

The approved target is `future_attack_state(t) = binary_attack_state(t + 10 seconds)` within the same `capture_day`. The current split uses 14-February and 21-February 2018 for training, 22-February for validation, and 28-February for the final test day.

Packet-level PCAP enrichment is intentionally not fused into V1. The available archive cannot currently be matched to the flow artifact with defensible machine or five-tuple provenance, so packet features are not fabricated.

## How Sentinel works

```text
Network flow telemetry
        ↓
Validated flow features
        ↓
10-second network states
        ↓
Temporal context window
        ↓
Multi-horizon forecast
        ↓
Warning · source priority · mitigation · explanation
```

The data and model boundary is defined by the versioned contracts in [docs/DATA_CONTRACT.md](docs/DATA_CONTRACT.md), [docs/NETWORK_STATE_SPEC.md](docs/NETWORK_STATE_SPEC.md), [docs/TARGET_STATE_SPEC.md](docs/TARGET_STATE_SPEC.md), and [docs/INFERENCE_CONTRACT.md](docs/INFERENCE_CONTRACT.md).

## Repository structure

```text
app/        Streamlit fallback and deterministic demo interface
configs/    Versioned feature and runtime configuration
data/       Raw, processed, and small sample-data locations
docs/       Contracts, architecture notes, decisions, audits, and runbooks
frontend/   Primary Next.js / React / TypeScript product interface
models/     Local model artifacts; checkpoints are ignored by Git
notebooks/  Exploratory work kept separate from production code
results/    Generated reports and evaluation artifacts
scripts/    Reproducibility, validation, and maintenance commands
src/        Ingestion, features, forecasting, inference, MITRE, and explainability
tests/      Automated tests
```

Raw datasets, processed datasets, model checkpoints, generated caches, and other large artifacts are excluded from Git. They must be acquired or generated locally according to the relevant data and runbook documentation.

## Run the primary interface

From the repository root, start the product UI with Docker Compose:

```bash
docker compose up -d --build
```

Open [http://localhost:3000](http://localhost:3000).

Stop the services with:

```bash
docker compose down
```

The primary interface keeps live telemetry and deterministic replay visibly separate. See [docs/FRONTEND_ARCHITECTURE.md](docs/FRONTEND_ARCHITECTURE.md).

## Run the Streamlit fallback

Install the project dependencies:

```bash
python -m pip install -r requirements.txt
```

Then start the fallback interface:

```bash
streamlit run app/streamlit_app.py
```

Use **Run Demo** to execute the deterministic local sequence at `data/samples/inference_demo_sequence.csv`, or upload a compatible 10-state sequence containing the approved 17 features, `timestamp`, and `capture_day` columns.

## Validate the repository

Install development dependencies and run the full test suite:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

The lightweight foundation checks are:

```bash
python scripts/smoke_test.py
python -m pytest tests/test_project_structure.py
```

## Operational language

Sentinel reports a **Forecast Score** and a **Predictive Warning** or **No Predictive Warning** state. The score is a model output, not a calibrated probability. The product does not claim that an attack has been detected, and recommendations are decision support rather than autonomous response.

## Further reading

- [Architecture](docs/ARCHITECTURE.md)
- [Network-state specification](docs/NETWORK_STATE_SPEC.md)
- [Target-state specification](docs/TARGET_STATE_SPEC.md)
- [World-model specification](docs/WORLD_MODEL_SPEC.md)
- [Inference contract](docs/INFERENCE_CONTRACT.md)
- [Frontend architecture](docs/FRONTEND_ARCHITECTURE.md)
- [Requirement matrix](docs/PS_REQUIREMENT_MATRIX.md)
- [Architecture decisions](docs/DECISIONS.md)
