"""Run the final offline source/network/forecast integrated demonstration."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.streaming.final_demo_engine import run_final_demo  # noqa: E402


DEFAULT_INPUT = PROJECT_ROOT / "data" / "samples" / "final_demo_events.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = run_final_demo(args.input)
    except (FileNotFoundError, OSError, ValueError, TypeError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print("NETWORK FORECAST")
    for row in result["network_forecast"]["forecasts"]:
        print(f"+{row['horizon_seconds']:>2}s: {float(row['score']):.6f}")
    print("\nNETWORK STATUS:")
    print(result["network_status"])
    print(f"Forecast Score threshold: {float(result['network_forecast']['threshold']):.2f}")
    print("\nSOURCE PRIORITIZATION")
    for row in result["source_priorities"]:
        print(f"{row['source_ip']}\n{row['priority']}\nReason: {row['measured_reasons']}\n")
    print("MITIGATION RECOMMENDATION")
    for row in result["mitigation_recommendations"]:
        print(f"{row['source_ip']}: {row['recommendation']}")
    print(f"\nSIMULATION ONLY: {str(result['simulation_only']).upper()}")
    print(f"States: {result['state_count']} | Total processing: {result['processing_time_ms']:.2f} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
