<div align="center">

# SENTINEL / NI

### Predict the next network state. Give operators time to respond.

**An open-source real-time network security platform for short-horizon
attack-state forecasting, source prioritization, and defensive decision
support.**

<sub>SIH26-26153 · v0.1.0 · 10-second network states · recommendation-only operations</sub>

</div>

<br />

> Network signals become state. State becomes context. Context becomes a
> decision surface—before the operator has to react.

Sentinel / NI converts network-flow telemetry into structured network states,
uses a frozen temporal model to forecast the next 50 seconds, and turns that
forecast into a focused operating view: **Forecast Score**, **Predictive
Warning / No Predictive Warning**, **Source Priority**, **Mitigation
Recommendation**, and model-sensitivity context.

## At a glance

| Contract | Current release |
| --- | --- |
| Release | `v0.1.0` |
| Network state interval | 10 seconds |
| Model context | `L=10` states |
| Forecast horizon | `K=5` · +10s / +20s / +30s / +40s / +50s |
| Model input | 17 numeric flow-derived features |
| Primary threshold | `0.19` |
| Input | CSE-CIC-IDS2018 multi-day flow data |
| Operations | Replay Mode and opt-in Live Mode |
| Mitigation | Recommendation-only · no automatic blocking |

## The product loop

```text
  NETWORK
     │
  PACKETS ──► FLOWS ──► NETWORK STATES
                              │
                         L=10 HISTORY
                              │
                          LSTM K=5
                              │
                           FORECAST
                    ┌─────────┼─────────┐
                    ▼         ▼         ▼
             SOURCE PRIORITY MITIGATION  API
                                          │
                                      DASHBOARD
```

The backend owns the processing session and inference path. The browser is a
consumer of structured results—it does not start a packet sniffer or run a
second model pipeline.

## What operators see

### Forecast

Five direct forecast points show the near-term network outlook at +10, +20,
+30, +40, and +50 seconds. The +10s result is the primary operating horizon.
Every result is presented as a **Forecast Score**—a model output, not a
calibrated probability.

### Operating warning

The configured policy maps the primary score to **Predictive Warning** or **No
Predictive Warning**. This is decision support, not confirmation of an event.

### Source prioritization

Observed activity is grouped into ranked **Candidate Sources**. A **Source
Priority** identifies what deserves review first; it does not prove identity or
replace analyst investigation.

### Mitigation

Mitigation is deliberately separate from source ranking. The current release
provides a **Mitigation Recommendation** only. It does not change firewall
rules, block traffic, or execute operator commands. Demonstration responses
keep **Simulation Only: TRUE** visible.

## Replay Mode and Live Mode

| Mode | Purpose | Data boundary |
| --- | --- | --- |
| **Replay Mode** | Deterministic demos, CI, and repeatable evaluation | Local approved sample/replay events |
| **Live Mode** | Host-level network observation | Metadata visible on one explicitly configured interface |

Replay is the safest way to evaluate the product. Live Mode is opt-in,
host-dependent, and requires Npcap on Windows or libpcap plus the necessary
permissions on Linux. It needs ten valid chronological 10-second states before
the first forecast is available.

## Start in minutes

### Option A — Docker Compose

```bash
docker compose up -d --build
```

Open the primary interface at [http://localhost:3000](http://localhost:3000).
The backend is available on port `8000`; the Streamlit fallback is on `8501`.

Stop the stack:

```bash
docker compose down
```

### Option B — local Python

```powershell
py -3.14 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
& .\.venv\Scripts\python.exe scripts\check_environment.py
& .\.venv\Scripts\python.exe -m pytest -q
```

Start the backend and fallback dashboard in separate terminals:

```powershell
& .\.venv\Scripts\python.exe -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000
& .\.venv\Scripts\python.exe -m streamlit run app\streamlit_app.py
```

The full clean-install workflow is documented in
[docs/REPRODUCIBLE_INSTALLATION.md](docs/REPRODUCIBLE_INSTALLATION.md).

### Run the deterministic replay

```powershell
python scripts/run_replay_demo.py --max-states 20 --speed 0
```

The command builds the bounded history and prints the five forecast horizons.
It does not download data or inspect live traffic. More copy-paste examples
are in [examples/README.md](examples/README.md).

## API surface

The FastAPI service exposes versioned endpoints for:

- health and readiness: `/api/v1/health`, `/api/v1/ready`;
- live state and telemetry controls: `/api/v1/live`, `/api/v1/telemetry/*`;
- forecasting: `/api/v1/forecast`;
- source review and mitigation recommendations;
- deterministic demonstration output: `POST /api/v1/demo`.

Interactive API documentation is available at `/docs` in development and is
disabled in production. See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) and
[docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) before exposing the
service.

## Frozen v0.1 contract

The approved target is:

```text
future_attack_state(t)
  = binary_attack_state(t + 10 seconds)
    within the same capture_day
```

Terminal states without a future +10s target are excluded. The day-aware split
is fixed: **2018-02-14 and 2018-02-21 for training**, **2018-02-22 for
validation**, and **2018-02-28 for final test**.

The frozen dataset contains **16,127 network states** and **17 flow-derived
features**. The exact feature order and target rules live in the versioned
contracts:

- [Data contract](docs/DATA_CONTRACT.md)
- [Network-state specification](docs/NETWORK_STATE_SPEC.md)
- [Target-state specification](docs/TARGET_STATE_SPEC.md)
- [Inference contract](docs/INFERENCE_CONTRACT.md)
- [Feature schema](configs/state_feature_schema.yaml)

## Data and security boundaries

Raw datasets, processed datasets, PCAP archives, model checkpoints, generated
caches, and local audit output are excluded from Git. They must be acquired or
generated locally under their own access and licensing rules.

PCAP enrichment is intentionally not fused into v0.1: the available archive
does not currently have defensible machine or five-tuple provenance connecting
it to the frozen flow artifact. Packet-level features are not fabricated.

Live capture follows a metadata-only principle: packet payload bytes are not
retained by the live adapter. Production configuration fails closed unless
authentication is enabled and all required role tokens are supplied. Read the
[security policy](SECURITY.md), [technical security boundaries](docs/SECURITY.md),
and [privacy notes](docs/PRIVACY.md) before using real traffic.

## Validate the repository

The v0.1 release was verified with:

```bash
python -m pytest -q
docker compose config
docker compose build
docker compose up -d
```

The final recorded result is **215 pytest tests passed**, with Docker health,
readiness, restart/recovery, frontend build, deterministic replay, and live
capture checks documented in the release reports.

- [Final release check](results/FINAL_V0_1_RELEASE_CHECK.md)
- [v0.1 freeze report](results/FINAL_V0_1_FREEZE_REPORT.md)
- [Public repository audit](results/PUBLIC_REPOSITORY_AUDIT.md)
- [Current limitations](docs/LIMITATIONS.md)

## Repository map

```text
app/        Streamlit fallback and deterministic demo interface
configs/    Versioned feature, model, and runtime configuration
data/       Local raw, processed, and sample-data locations
docs/       Contracts, architecture, operations, and security guidance
examples/   Safe copy-paste usage examples
frontend/   Primary Next.js / React / TypeScript interface
models/     Local model artifacts; checkpoints are Git-ignored
scripts/    Reproducibility, validation, and maintenance commands
src/        Ingestion, features, forecasting, inference, and telemetry
tests/      Automated regression and contract tests
```

## Documentation

| Start here | Go deeper |
| --- | --- |
| [Architecture](docs/ARCHITECTURE.md) | [Real-time product architecture](docs/REALTIME_PRODUCT_ARCHITECTURE.md) |
| [Deployment guide](docs/DEPLOYMENT_GUIDE.md) | [Live operation](docs/LIVE_OPERATION.md) |
| [Model contract](docs/MODEL.md) | [Forecasting](docs/FORECASTING.md) |
| [Telemetry](docs/TELEMETRY.md) | [Troubleshooting](docs/TROUBLESHOOTING.md) |
| [Source prioritization](docs/SOURCE_PRIORITIZATION.md) | [Mitigation](docs/MITIGATION.md) |
| [Privacy](docs/PRIVACY.md) | [Security](SECURITY.md) |

## Roadmap

The next release can add longer live-soak evidence, stronger queue and
flow-table observability, drift monitoring, broader telemetry adapters, and an
authoritative PCAP-to-flow attribution path. Enterprise identity, high
availability, and automatic enforcement require separate security and
deployment work.

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a change. Keep
the frozen data/model contracts explicit, run the relevant validation gates,
and never submit datasets, PCAPs, checkpoints, credentials, private traffic,
or personal filesystem paths.

## License

Project-owned code is released under the [MIT License](LICENSE). Dataset, PCAP,
and model-artifact terms are separate; contributors must have the right to
share anything they submit.

<div align="center">

<sub>Sentinel / NI · Forecast first. Respond deliberately.</sub>

</div>
