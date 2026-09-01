# Sentinel / NI

**An open-source real-time network security platform for short-horizon
attack-state forecasting, source prioritization, and defensive decision
support.**

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
NETWORK
   ↓
PACKETS → FLOWS → NETWORK STATES
                         ↓
                    L=10 history
                         ↓
                    LSTM K=5
                         ↓
                    FORECAST
                  ↙      ↓       ↘
       SOURCE PRIORITY  MITIGATION  API
                                      ↓
                                  DASHBOARD
```

The current release has two operating surfaces. **Replay Mode** runs the
deterministic local demonstration path for repeatable evaluation. **Live Mode**
reads metadata visible on one explicitly configured host interface and begins
forecasting only after a valid ten-state history is available. The backend owns
the processing session; the browser does not capture packets or run inference.

## Model and Forecast Score

The serving model is the frozen LSTM K=5 checkpoint over a ten-state, ten-second
history. It emits five direct horizons at +10, +20, +30, +40, and +50 seconds.
Each result is a **Forecast Score**, not a calibrated probability. The operating
policy presents **Predictive Warning** or **No Predictive Warning** according to
the configured threshold.

## Source Prioritization and Mitigation

Sentinel ranks observed **Candidate Sources** by measured activity signals so
an operator can decide what to review first. A **Source Priority** is review
evidence, not attacker identification. **Mitigation** is a separate,
recommendation-only output; the current release never changes firewall rules or
automatically blocks traffic. Demo responses keep **Simulation Only: TRUE**
visible.

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

## Configuration and API

Runtime configuration is environment-driven. See
[docs/CONFIGURATION.md](docs/CONFIGURATION.md) and
[docs/REPRODUCIBLE_INSTALLATION.md](docs/REPRODUCIBLE_INSTALLATION.md) for
fresh-environment commands. The FastAPI service exposes `/api/v1/health`,
`/api/v1/ready`, `/api/v1/live`, `/api/v1/forecast`, source prioritization,
mitigation recommendations, and telemetry controls. API documentation is
available at `/docs` in development and disabled in production.

The model serves a frozen 17-feature, 10-second, L=10, K=5 contract. Source
prioritization is candidate-source review evidence, and mitigation is
recommendation-only with no automatic blocking. See the model, forecasting,
source, and mitigation documents under `docs/` for the exact boundaries.

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

## Live operation and security

Live mode monitors only traffic visible to the explicitly configured sensor
interface. The backend owns one shared runtime for all dashboard readers; the
browser never starts a second packet sniffer or runs a second model pipeline.
See [docs/LIVE_OPERATION.md](docs/LIVE_OPERATION.md),
[docs/REALTIME_PRODUCT_ARCHITECTURE.md](docs/REALTIME_PRODUCT_ARCHITECTURE.md),
[docs/PRIVACY.md](docs/PRIVACY.md), and [SECURITY.md](SECURITY.md) before
exposing the service.

Production configuration fails closed when authentication is disabled. Local
development may use the default development profile, but an exposed
deployment must set `SIH_ENV=production`, enable authentication, and provide
all three role tokens. This open-source release is governed by the [MIT
License](LICENSE) for project-owned code.
Datasets, PCAPs, and model artifacts remain separately governed and are not
redistributed by this repository.

## Further reading

- [Architecture](docs/ARCHITECTURE.md)
- [Network-state specification](docs/NETWORK_STATE_SPEC.md)
- [Target-state specification](docs/TARGET_STATE_SPEC.md)
- [World-model specification](docs/WORLD_MODEL_SPEC.md)
- [Inference contract](docs/INFERENCE_CONTRACT.md)
- [Frontend architecture](docs/FRONTEND_ARCHITECTURE.md)
- [Requirement matrix](docs/PS_REQUIREMENT_MATRIX.md)
- [Architecture decisions](docs/DECISIONS.md)
- [Real-time product architecture](docs/REALTIME_PRODUCT_ARCHITECTURE.md)
- [Live operation](docs/LIVE_OPERATION.md)
- [Security policy](SECURITY.md)
- [Privacy and retention](docs/PRIVACY.md)
- [Current limitations](docs/LIMITATIONS.md)

## Roadmap

The next release can add longer live soak evidence, stronger runtime
observability, drift monitoring, broader telemetry adapters, and an
authoritative PCAP-to-flow attribution path. Automatic enforcement, enterprise
identity, and high availability require separate security and deployment work.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development workflow, validation
commands, and scope boundaries. Please do not submit datasets, PCAPs, model
checkpoints, secrets, or private traffic captures.

## License

Project-owned code is released under the [MIT License](LICENSE). Dataset,
PCAP, and model-artifact terms are separate; contributors must have the right
to share anything they submit.
