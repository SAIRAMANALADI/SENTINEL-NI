# Clean Installation Validation

## Status

PASS WITH LIMITATIONS — the isolated Python installation, frontend build, and
Docker runtime validation passed. The release still has host-dependent live
capture limitations documented in the final release check.

## Exact verification commands

```powershell
git clone <repository-url>
cd SIH26
py -3.14 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
Copy-Item .env.example .env
& .\.venv\Scripts\python.exe scripts\check_environment.py
& .\.venv\Scripts\python.exe -m pytest -q
cd frontend
npm ci
npm run typecheck
npm run build
cd ..
docker compose config
docker compose up -d --build
Invoke-RestMethod http://localhost:8000/api/v1/health
Invoke-RestMethod http://localhost:8000/api/v1/ready
Start-Process http://localhost:3000
```

For replay mode, set `SIH_TELEMETRY_MODE=replay` in the environment before
starting the backend. For production, also set `SIH_ENV=production`, enable
authentication, and provide all role tokens.

## Evidence available in this workspace

- Fresh isolated virtual environment: install completed from
  `requirements.lock.txt`.
- `pip check`: passed — no broken requirements.
- `scripts/check_environment.py`: passed.
- Full isolated suite: 215 passed in 74.36 seconds.
- Frontend `npm ci`: passed — 29 packages installed, 0 vulnerabilities.
- Frontend typecheck: passed.
- Frontend production build: passed.
- `docker compose config`: passed.
- Docker daemon runtime: passed — Compose build, startup, health/readiness,
  restart, down/up recovery, and dashboard/frontend health all passed.
