# Examples

These examples use local, deterministic inputs and do not download datasets or
PCAPs.

## Replay demo

From the repository root:

```powershell
python scripts/run_replay_demo.py --max-states 20 --speed 0
```

The command builds the bounded state history and prints the +10/+20/+30/+40/
+50 Forecast Scores. It is replay/demo output, not live telemetry.

## API smoke check

With the backend running locally:

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/health
Invoke-RestMethod http://localhost:8000/api/v1/ready
Invoke-RestMethod http://localhost:8000/api/v1/demo -Method Post
```

## Live mode

Discover an interface first:

```powershell
python scripts/list_capture_interfaces.py --json
$env:SIH_TELEMETRY_MODE = "live"
$env:SIH_TELEMETRY_INTERFACE = "<exact-interface-name>"
python -m uvicorn src.api.app:app --host 127.0.0.1 --port 8000
```

Live mode requires host capture support such as Npcap on Windows or libpcap
and the required permission on Linux. It observes metadata only and needs ten
valid 10-second states before the first forecast.
