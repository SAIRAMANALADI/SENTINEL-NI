"""Short local live-capture smoke test; packet payloads are never retained."""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.telemetry.live import LiveTelemetryAdapter, LiveTelemetryError, discover_capture_interfaces


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interface", default=os.getenv("SIH_TELEMETRY_INTERFACE"))
    parser.add_argument("--duration", type=float, default=10.0)
    args = parser.parse_args()
    if args.duration <= 0 or args.duration > 10:
        parser.error("--duration must be greater than 0 and no more than 10 seconds")
    try:
        interfaces = discover_capture_interfaces()
        names = {row["name"] for row in interfaces}
        if not args.interface:
            print("No interface selected. Re-run with --interface <exact discovered name>.")
            print("Discovered interfaces:")
            for row in interfaces:
                print(f"- {row['name']} ({row['status']})")
            return 2
        if args.interface not in names:
            print(f"Interface not found: {args.interface}")
            return 2
        adapter = LiveTelemetryAdapter(args.interface)
        started = time.perf_counter()
        adapter.start()
        count = 0
        while time.perf_counter() - started < args.duration:
            while adapter.read_event() is not None:
                count += 1
            time.sleep(0.05)
        adapter.stop()
        final_status = adapter.status()
        print(f"interface={args.interface}")
        print(f"duration_seconds={args.duration:.2f}")
        print(f"events_emitted={count}")
        print(f"status={final_status['status']}")
        if final_status["status"] == "LIVE_ERROR":
            print(f"error={final_status.get('error')}")
            return 1
        return 0
    except LiveTelemetryError as exc:
        print(f"LIVE_CAPTURE_FAILED: {exc}")
        return 1
    finally:
        if "adapter" in locals():
            adapter.stop()


if __name__ == "__main__":
    raise SystemExit(main())
