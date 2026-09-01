# Live Operation

Live mode observes traffic visible to the configured sensor interface, such
as a server NIC, SPAN/mirror port, TAP, or another supported adapter. It does
not claim visibility into traffic that the host cannot receive.

## Host prerequisites

- Python 3.12 or later within the supported range.
- Scapy installed from `requirements.txt`.
- Windows: Npcap installed and capture permission granted.
- Linux: libpcap and the minimum required capture capability.
- An exact interface name from:

```powershell
python scripts/list_capture_interfaces.py --json
```

## Configuration

Set the interface and live mode in the service environment:

```powershell
$env:SIH_ENV = "development"
$env:SIH_TELEMETRY_MODE = "live"
$env:SIH_TELEMETRY_INTERFACE = "<exact-interface-name>"
```

For an exposed deployment, use production mode and provide all role tokens:

```powershell
$env:SIH_ENV = "production"
$env:SIH_AUTH_ENABLED = "true"
$env:SIH_VIEWER_TOKEN = "<random-viewer-token>"
$env:SIH_OPERATOR_TOKEN = "<random-operator-token>"
$env:SIH_ADMIN_TOKEN = "<random-admin-token>"
```

Start capture through the operator API after the backend is running:

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/telemetry/start `
  -Method Post -Headers @{Authorization="Bearer <operator-token>"}
```

The runtime resets its active state and creates a new `session_id` for every
start. It needs ten valid, chronological 10-second states before the first
forecast. The API reports this as a bounded history state rather than
inventing a forecast.

Inspect status with:

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/live `
  -Headers @{Authorization="Bearer <viewer-token>"}
```

Stopping capture marks the last forecast stale; it is never presented as
current live data. Restarting starts a clean session and cannot reuse the
previous session's history.
