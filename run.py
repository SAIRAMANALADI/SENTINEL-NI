"""Run one offline network-state inference request."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.forecasting.inference import predict_network_state_sequence  # noqa: E402


def _load_input(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    if path.suffix.lower() in {".csv", ".tsv"}:
        return pd.read_csv(path, sep="\t" if path.suffix.lower() == ".tsv" else ",")
    raise ValueError("input must be a .parquet, .csv, or .tsv file")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--top-n", type=int, default=5)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = predict_network_state_sequence(_load_input(args.input), top_n=args.top_n)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    except (FileNotFoundError, ValueError, TypeError, KeyError, OSError, pd.errors.ParserError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"Model: {result['model_version']}")
    print(f"Reference: {result['reference_timestamp']} | Mode: {result['operating_mode']} | Threshold: {result['threshold']:.2f}")
    for row in result["forecast"]:
        state = "Predictive warning" if row["warning"] else "No predictive warning"
        print(f"+{row['horizon_seconds']:>2}s: score={row['score']:.6f} | {state}")
    if args.output:
        print(f"JSON: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
