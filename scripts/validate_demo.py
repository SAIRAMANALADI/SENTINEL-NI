"""Validate the frozen offline demo contract without training or changing data."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.forecasting.inference import predict_network_state_sequence


DEFAULT_INPUT = PROJECT_ROOT / "data" / "samples" / "inference_demo_sequence.csv"


def main() -> int:
    try:
        result = predict_network_state_sequence(pd.read_csv(DEFAULT_INPUT))
    except (FileNotFoundError, OSError, TypeError, ValueError, pd.errors.ParserError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if len(result["forecast"]) != 5:
        print("ERROR: demo did not return five forecast rows", file=sys.stderr)
        return 2
    if [row["horizon_seconds"] for row in result["forecast"]] != [10, 20, 30, 40, 50]:
        print("ERROR: demo horizon contract is invalid", file=sys.stderr)
        return 2
    json.dumps(result)
    print("Demo validation: PASS")
    print(f"Model: {result['model_version']}")
    print(f"Mode: {result['operating_mode']} | Threshold: {result['threshold']:.2f}")
    print("Horizons: +10s, +20s, +30s, +40s, +50s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
