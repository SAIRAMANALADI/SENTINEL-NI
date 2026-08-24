"""Run the frozen inference API over a deterministic offline replay source."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.streaming.realtime_engine import RealtimeEngine  # noqa: E402
from src.streaming.replay import iter_replay_events  # noqa: E402


DEFAULT_INPUT = PROJECT_ROOT / "data" / "samples" / "inference_demo_sequence.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="approved state or flow replay source")
    parser.add_argument(
        "--speed",
        type=float,
        default=0.0,
        help="virtual replay speed factor; 0 runs without wall-clock sleep, 5 sleeps about 2 seconds per state",
    )
    parser.add_argument("--max-states", type=int, default=120, help="maximum emitted states")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.speed < 0:
        print("ERROR: --speed must be non-negative", file=sys.stderr)
        return 2
    if args.max_states < 1:
        print("ERROR: --max-states must be positive", file=sys.stderr)
        return 2

    engine = RealtimeEngine()
    previous_timestamp = None
    try:
        events = iter_replay_events(args.input)
        for update in engine.replay(events, max_states=args.max_states):
            if args.speed > 0 and previous_timestamp is not None:
                time.sleep(10.0 / args.speed)
            previous_timestamp = update.timestamp
            timestamp = update.timestamp or "UNKNOWN"
            if update.inference_result is None:
                print(f"{timestamp} | {update.status} | waiting for exactly 10 valid states")
                if update.reason:
                    print(f"  reason: {update.reason}")
                continue
            result = update.inference_result
            print(
                f"{timestamp} | Forecast Score {float(result['forecast'][0]['score']):.6f} | "
                f"{('Predictive warning' if result['forecast'][0]['warning'] else 'No predictive warning')} | "
                f"forecast horizon +{result['forecast_horizon_seconds']}s | "
                f"processing {update.processing_ms:.2f}ms"
            )
            for row in result["forecast"]:
                state = "Predictive warning" if row["warning"] else "No predictive warning"
                print(f"  +{row['horizon_seconds']:>2}s: score={row['score']:.6f} | {state}")
    except (FileNotFoundError, OSError, ValueError, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
