# Development Guide

## Repository structure

| Path | Purpose |
| --- | --- |
| `app/` | Streamlit fallback and prepared demonstration interface |
| `src/api/` | Central FastAPI service, contracts, auth, and runtime endpoints |
| `src/agent/` | Remote Sentinel Agent CLI, capture, buffering, and delivery |
| `src/features/` | Frozen flow/state feature construction |
| `src/forecasting/` | Frozen inference and temporal windowing |
| `src/sensors/` | Sensor registry and isolated remote runtimes |
| `configs/` | Versioned feature, target, policy, and project contracts |
| `data/` | Local datasets and small approved fixtures; large artifacts are ignored |
| `models/` | Local checkpoints; most artifacts are ignored |
| `frontend/` | Next.js dashboard |
| `tests/` | Unit, API, integration, security, and contract tests |
| `docs/` | Architecture, operator, deployment, and release documentation |

## Python setup and checks

```powershell
py -3.14 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
& .\.venv\Scripts\python.exe scripts/check_environment.py
& .\.venv\Scripts\python.exe scripts/release_audit.py
& .\.venv\Scripts\python.exe -m pytest -q
```

Build distributions with `python -m build --wheel --sdist`. Inspect `dist/`
before sharing an artifact.

## Central runtime

For local development:

```powershell
$env:SIH_ENV = "development"
$env:SIH_TELEMETRY_MODE = "mock"
python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000
```

Verify `GET /api/v1/health` and `GET /api/v1/ready`. Use
`scripts/run_replay_demo.py` for deterministic offline data and
`scripts/run_final_demo.py` for the prepared demonstration path.

## Frontend

```powershell
Set-Location frontend
npm ci
npm run typecheck
npm run build
npm run dev
```

The frontend talks to the central API; it never connects directly to a
remote agent.

## Agent and telemetry modes

The installed agent commands are documented in
[Operator Quickstart](OPERATOR_QUICKSTART.md). The central service also
supports replay/mock modes and a host-level live capture path. Live capture
requires an approved interface and Npcap/libpcap; tests use bounded fakes and
must not be described as a physical live soak.

## Change boundaries

The 17-feature state schema, target semantics, L=10 context, K=5 horizons, and
threshold `0.19` are frozen for this release. Changes crossing those contracts
need a versioned technical review, new evidence, and explicit documentation.
