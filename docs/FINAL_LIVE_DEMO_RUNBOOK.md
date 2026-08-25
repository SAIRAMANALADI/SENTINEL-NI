# Final Live Demo Runbook

This runbook separates the deterministic review path from real host capture.
The deterministic path is suitable for a repeatable 2–3 minute judge review.
Real capture is evidence-backed but traffic-dependent; the latest measured run
needed 296.97 seconds to reach the first inference.

## 1. Start the Docker backend and dashboard

From the repository root:

```powershell
docker compose down
$env:DASHBOARD_PORT = "8512"
docker compose up -d
docker compose ps
Invoke-RestMethod http://localhost:8000/api/v1/ready
Invoke-WebRequest http://localhost:8512/_stcore/health -UseBasicParsing
```

`DASHBOARD_PORT=8512` avoids a host-specific conflict if port 8501 is already
in use. The compose backend is intentionally configured with
`SIH_TELEMETRY_MODE=mock`; it validates the deployable API/dashboard path but
does not provide host Npcap capture inside the container.

## 2. Deterministic 2–3 minute review

Open `http://localhost:8512` and choose the clearly labelled mode:

1. `REPLAY · DETERMINISTIC REPLAY` for the validated replay path;
2. start replay and show the 10-state progression;
3. show `FORECAST READY` and the +10/+20/+30/+40/+50 Forecast Scores;
4. show Predictive warning or No predictive warning;
5. show Candidate Source priorities and the mitigation recommendation;
6. expand Explanation / Technical Details if needed;
7. choose `MOCK / STATIC` to show the deterministic demo/test-data fallback;
8. choose `Full Integrated Demo` to run the backend-mediated full demo.

## 3. Real host capture review

Npcap/Scapy capture runs on the Windows host. Start a host API on port 8005:

```powershell
$env:SIH_API_PORT = "8005"
$env:SIH_TELEMETRY_MODE = "live"
$env:SIH_TELEMETRY_INTERFACE = "Wi-Fi"
$env:SIH_AUTH_ENABLED = "false"
Start-Process python -ArgumentList @(
  "-m", "uvicorn", "src.api.app:app", "--host", "127.0.0.1", "--port", "8005"
) -WorkingDirectory (Get-Location) -WindowStyle Hidden

$env:SIH_API_URL = "http://127.0.0.1:8005"
python -m streamlit run app/streamlit_app.py --server.address 127.0.0.1 --server.port 8511
```

Open `http://127.0.0.1:8511`, choose `LIVE · REAL CAPTURE`, and choose the
configured `Wi-Fi` interface. Then:

1. click `START LIVE CAPTURE`;
2. show packet quality, packets seen, valid events, ignored events, flow count;
3. show `BUILDING NETWORK HISTORY · N / 10 states`;
4. wait for `FORECAST READY` (do not invent an ETA);
5. show all five actual Forecast Scores and the threshold;
6. show Candidate Source priorities and mitigation with `Simulation only: TRUE`;
7. expand the explanation and startup timing details;
8. click `STOP LIVE CAPTURE` and verify `STALE` / `LIVE_STOPPED`;
9. click `START LIVE CAPTURE` again and verify the state buffer resets to 0/10;
10. wait for new history before treating a forecast as current.

## 4. Backend outage check

Stop the API process or backend container, refresh the dashboard, and verify
`BACKEND UNAVAILABLE`. Restart it and verify the dashboard returns to a
healthy waiting or ready state. Cached output must not be presented as current
live data.

## 5. Terminology

Use Forecast Score, Predictive warning, Candidate Source, High Priority
Source, Mitigation Recommendation, Simulation Only, LIVE, and STALE. Do not
describe a score as a calibrated probability or a source as an attacker.
