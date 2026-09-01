# Sensor Installation

Prerequisites: a supported Python version, Scapy and Npcap/libpcap on the
connected server, capture permission, and HTTPS network access to the central
API.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m src.agent init --server-url https://central.example --interface "Ethernet"
python -m src.agent register --enrollment-token <one-time-token>
python -m src.agent start
```

The token is consumed once. Protect the generated configuration and runtime
credential with operating-system file permissions. The agent emits completed
states, not raw packets.
