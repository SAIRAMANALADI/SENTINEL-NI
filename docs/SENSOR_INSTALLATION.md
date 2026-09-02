# Sensor Installation

Prerequisites: a supported Python version, Scapy and Npcap/libpcap on the
connected server, capture permission, and HTTPS network access to the central
API. Phase B keeps enrollment on the server-side administration path; the
browser does not receive a global administrator token.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m src.agent init --server-url https://central.example --interface "Ethernet" --environment production
python -m src.agent register --enrollment-token <one-time-token>
python -m src.agent status
python -m src.agent start
```

An administrator creates the one-time enrollment credential through the
authenticated `POST /api/v1/sensors/enrollment` control-plane operation, using
an administrator-only server-side client or the command in
`docs/DEPLOYMENT_GUIDE.md`. Do not place the administrator token in browser
JavaScript, URLs, logs, or the agent installation commands.

The token is consumed once. Protect the generated configuration and runtime
credential with operating-system file permissions. The agent emits completed
states, not raw packets.

The agent runs on the monitored host and observes its interface out-of-band;
the customer's application continues to serve its own requests directly. It
does not expose or proxy application traffic through Sentinel. The central
service accepts version-1 state batches and the dashboard displays only the
selected sensor's health and forecast.

For local development only, `--environment development` permits an `http://`
central URL. Production agent configuration fails closed unless the server URL
uses `https://`; HTTP is never silently upgraded.

Reliability settings are written into the agent configuration at initialization
and can be reviewed with `python -m src.agent config`. The available controls
include batch size/interval, heartbeat interval, buffer batch/byte limits,
`DROP_OLDEST` or `REJECT_NEW`, retry base/max delay, and optional retry jitter.
Keep the buffer directory on durable local storage and restrict its filesystem
permissions. The queue is bounded at-least-once delivery, not exactly-once.
