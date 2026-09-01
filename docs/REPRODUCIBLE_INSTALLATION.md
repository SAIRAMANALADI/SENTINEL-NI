# Reproducible Installation

The supported runtime is Python `>=3.12,<3.15`. The repository keeps the
human-maintained compatibility ranges in `requirements.txt` and the exact
tested dependency set in `requirements.lock.txt`.

## Fresh Python environment

From a clean clone:

```powershell
py -3.14 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
& .\.venv\Scripts\python.exe scripts\check_environment.py
& .\.venv\Scripts\python.exe -m pytest -q
```

On Linux, use the equivalent `python3.14 -m venv .venv` and
`.venv/bin/python` commands. The lock file currently records the versions
verified on Python 3.14; it is an exact-version lock but does not yet include
package hashes or a separately signed artifact index.

## Frontend

From `frontend/`:

```bash
npm ci
npm run typecheck
npm run build
```

The checked-in `frontend/package-lock.json` is the authoritative frontend
dependency lock.

## Docker

Docker provides the one-command local service path:

```bash
docker compose config
docker compose build
docker compose up -d --build
```

The default Compose profile uses mock telemetry for safe local startup. Set
`SIH_TELEMETRY_MODE=replay` for deterministic replay, or follow
[LIVE_OPERATION.md](LIVE_OPERATION.md) for host-level live capture. For an
exposed deployment set `SIH_ENV=production`, `SIH_AUTH_ENABLED=true`, and all
three role tokens before starting the stack.

## Dependency correction

The development dependency is the published `httpx` package used by the
FastAPI test client. No private package index or developer-local package is
required.
