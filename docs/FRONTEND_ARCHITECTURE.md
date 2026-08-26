# Frontend Architecture

## Product boundary

The primary judge-facing interface is a standalone Next.js/React/TypeScript application in `frontend/`. Streamlit remains available on port 8501 as a fallback and internal development interface; it is not the release product surface.

The frontend does not implement forecasting, source attribution, mitigation policy, thresholds, feature transformation, or target logic. The existing FastAPI service remains authoritative for all operational values.

## Runtime topology

```text
Browser :3000
    -> Next.js same-origin /api/* rewrite
    -> FastAPI backend :8000
    -> existing inference, policy, telemetry, and audit paths
```

The rewrite avoids browser CORS coupling. `BACKEND_URL` is set to `http://backend:8000` in Compose and defaults to `http://127.0.0.1:8000` for local development.

## UI composition

- `CommandCenter`: live polling, mode selection, primary hierarchy, and error handling.
- `ForecastView`: +10s primary forecast, compact +10/+20/+30/+40/+50 rail, trajectory chart, threshold, and sensitivity explanation.
- `SourceIntelligence`: ranked candidate source evidence and separate recommendation-only mitigation cards.
- `StatusPill`: consistent runtime and data-state language.
- `ReplayPanel`: explicit backend-mediated deterministic replay; never labelled as live telemetry.

The visual system is handwritten CSS rather than a generic component library: dark neutral surfaces, restrained cyan/amber/red operational accents, mono data labels, editorial spacing, and responsive breakpoints for laptop and desktop screens. Fonts use local system stacks so the product does not depend on an external font request.

## API contract used

- `GET /api/v1/ready`: readiness gate.
- `GET /api/v1/live`: polled every 5 seconds for telemetry, state buffer, forecast, source priorities, mitigation, and errors.
- `POST /api/v1/demo`: explicit controlled fixture used only by Overview/Replay actions.

An optional `NEXT_PUBLIC_SIH_API_TOKEN` is sent as a bearer token. Compose leaves authentication disabled by default for the local demo; production deployment must provide a real identity/secret-management boundary and TLS.

## Truthfulness rules

- Live telemetry and replay are visually and textually distinct.
- `Forecast Score` is never described as a calibrated probability.
- The UI uses `Predictive warning` / `No predictive warning`, never an attack-detected claim.
- Candidate sources are ranked evidence, not confirmed attribution.
- Mitigation is recommendation-only; automatic blocking is not exposed.
- Backend-unavailable, stopped, stale, and insufficient-history states are explicit.

## Run

From the repository root:

```powershell
docker compose up -d --build
Start-Process http://localhost:3000
```

For frontend-only development with the backend already running:

```powershell
cd frontend
npm ci
npm run dev
```

Use `http://localhost:3000`. The legacy fallback remains `streamlit run app/streamlit_app.py` on port 8501.

## Deliberate limitations

The page is a viewer and operator-review surface; it does not start packet capture or add a second inference implementation. Local Compose uses mock telemetry and disabled authentication unless explicitly configured. Real live capture remains dependent on the backend host adapter and its existing permissions.
