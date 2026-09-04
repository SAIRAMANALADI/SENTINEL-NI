"""Monitor-only validation harness for a real remote sensor forecast run.

The harness never posts telemetry and never mutates central runtime state. Run
it alongside the actual ``sentinel-agent`` process; it polls the authenticated
sensor detail and forecast endpoints and emits JSON snapshots suitable for a
validation record.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
import time
from typing import Any

import httpx


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="central API base URL")
    parser.add_argument("--sensor-id", required=True)
    parser.add_argument("--ca", help="CA bundle for HTTPS verification")
    parser.add_argument("--token-env", default="SIH_VIEWER_TOKEN", help="environment variable holding the viewer token")
    parser.add_argument("--polls", type=int, default=1)
    parser.add_argument("--interval", type=float, default=10.0)
    return parser


def _snapshot(client: httpx.Client, base_url: str, sensor_id: str) -> dict[str, Any]:
    detail = client.get(f"{base_url}/api/v1/sensors/{sensor_id}")
    detail.raise_for_status()
    payload = detail.json()
    runtime = payload.get("runtime") or {}
    forecast = runtime.get("forecast") or {}
    rows = list(forecast.get("forecast") or [])
    history_length = runtime.get("history_length", 0)
    history_required = runtime.get("history_required", 10)
    forecast_status = runtime.get("forecast_status")
    return {
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "sensor_id": payload.get("sensor_id"),
        "status": payload.get("status"),
        "agent_status": payload.get("agent_status"),
        "telemetry_status": payload.get("telemetry_status"),
        "last_telemetry": payload.get("last_telemetry"),
        "telemetry_sequence": {
            "last_sequence": payload.get("last_sequence"),
            "last_accepted_sequence": payload.get("last_accepted_sequence"),
            "last_sent_sequence": payload.get("last_sent_sequence"),
            "buffered_item_count": payload.get("buffered_item_count", 0),
        },
        "last_state_timestamp": runtime.get("latest_state_timestamp"),
        "state_count": runtime.get("state_count", 0),
        "state_timestamps_observed": [runtime.get("latest_state_timestamp")]
        if runtime.get("latest_state_timestamp")
        else [],
        "history_length": history_length,
        "history_required": history_required,
        "l10_readiness": "READY" if history_length >= history_required else "WAITING",
        "forecast_status": forecast_status,
        "dashboard_ready_state_from_runtime": (
            "FORECAST_READY" if forecast_status == "FORECAST_READY" else "FORECAST_WAITING"
        ),
        "forecast_update_count": runtime.get("forecast_update_count", 0),
        "forecast_rows": len(rows),
        "forecast_timestamps": [row.get("timestamp") for row in rows],
        "forecast_scores": [row.get("score") for row in rows],
        "warning_states": [row.get("warning") for row in rows],
    }


def main() -> int:
    args = _parser().parse_args()
    if args.polls < 1 or args.interval < 0:
        raise SystemExit("--polls must be positive and --interval must not be negative")
    token = os.environ.get(args.token_env)
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    verify: str | bool = args.ca or True
    base_url = args.base_url.rstrip("/")
    with httpx.Client(headers=headers, verify=verify, trust_env=False, timeout=10.0) as client:
        for index in range(args.polls):
            print(json.dumps(_snapshot(client, base_url, args.sensor_id), sort_keys=True))
            if index + 1 < args.polls:
                time.sleep(args.interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
