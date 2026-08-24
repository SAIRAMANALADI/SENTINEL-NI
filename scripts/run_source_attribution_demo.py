"""Run the deterministic source-attribution mock stream audit."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.mitigation_policy import recommendations_for_sources  # noqa: E402
from src.evaluation.rate_limit_simulator import simulate_rate_limit  # noqa: E402
from src.streaming.replay import iter_packet_replay_events  # noqa: E402
from src.streaming.source_activity import aggregate_source_activity  # noqa: E402
from src.streaming.source_forecast import prioritize_sources  # noqa: E402


DEFAULT_INPUT = PROJECT_ROOT / "data" / "samples" / "source_attribution_mock.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        events = list(iter_packet_replay_events(args.input))
        packet_rows = [event.payload for event in events]
        activity = aggregate_source_activity(packet_rows)
        network_context = {
            "reference_timestamp": "2018-02-22T01:00:39",
            "forecast": [{"step": 1, "score": 0.8, "warning": True}],
        }
        prioritized = prioritize_sources(activity, network_context)
        latest_by_source = (
            prioritized.sort_values(["source_ip", "interval_start"], kind="mergesort")
            .groupby("source_ip", sort=True, as_index=False)
            .tail(1)
            .sort_values("source_ip", kind="mergesort")
        )
        recommendations = recommendations_for_sources(latest_by_source.to_dict(orient="records"))
        simulation = simulate_rate_limit("10.0.0.3", 350.0, 50.0)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"Packet events: {len(events)}")
    print(f"Activity rows: {len(activity)}")
    print(latest_by_source[["source_ip", "priority", "priority_points", "measured_reasons"]].to_string(index=False))
    print("Mitigation recommendations:")
    for row in recommendations:
        print(f"  {row['source_ip']}: {row['recommendation']} ({row['risk_status']})")
    print(
        "Rate-limit simulation: "
        f"{simulation['original_traffic_rate']:.2f} -> {simulation['simulated_allowed_rate']:.2f} rate, "
        f"throttled={simulation['throttled_amount']:.2f}, reduction={simulation['percentage_reduction']:.2f}%"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
