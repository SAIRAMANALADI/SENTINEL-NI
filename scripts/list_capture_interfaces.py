"""Discover capture interfaces without starting a packet capture."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.telemetry.live import LiveTelemetryError, discover_capture_interfaces


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    try:
        interfaces = discover_capture_interfaces()
    except LiveTelemetryError as exc:
        print(json.dumps({"status": "LIVE_UNAVAILABLE", "error": str(exc)}))
        return 2
    if args.as_json:
        print(json.dumps(interfaces, indent=2))
    else:
        print("NAME\tSTATUS\tCAPTURE AVAILABLE\tADDRESS\tDESCRIPTION")
        for row in interfaces:
            print(
                f"{row['name']}\t{row['status']}\t{row['capture_available']}\t"
                f"{row['address']}\t{row['description']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
