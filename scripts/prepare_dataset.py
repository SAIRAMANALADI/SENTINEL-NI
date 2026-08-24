"""Validate a local dataset input and prepare an empty processed directory."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def validate_input(input_path: Path) -> Path:
    """Return an existing local file or directory, with a clear failure."""
    input_path = input_path.expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Dataset input does not exist: {input_path}")
    return input_path


def read_csv_header(input_path: Path) -> list[str]:
    """Read only a CSV header; never load the dataset into memory."""
    if input_path.suffix.lower() != ".csv":
        raise ValueError(f"Expected a CSV file for header inspection: {input_path}")
    with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
        header = next(csv.reader(handle), None)
    if not header:
        raise ValueError(f"CSV has no header: {input_path}")
    return [column.strip() for column in header]


def validate_expected_columns(header: list[str], expected_columns: list[str]) -> None:
    missing = [column for column in expected_columns if column not in header]
    if missing:
        raise ValueError(f"Required CSV columns are missing: {', '.join(missing)}")


def prepare_processed_directory(processed_directory: Path) -> Path:
    """Create and return the repository processed-data directory."""
    processed_directory.mkdir(parents=True, exist_ok=True)
    return processed_directory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a local dataset input without transforming or downloading it."
    )
    parser.add_argument("--input", required=True, type=Path, help="Explicit local file or directory.")
    parser.add_argument(
        "--expected-column",
        action="append",
        default=[],
        help="Expected CSV column; repeat as needed when --input is a CSV.",
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "processed",
        help="Repository processed-data directory to create.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        input_path = validate_input(args.input)
        header = None
        if input_path.is_file() and input_path.suffix.lower() == ".csv":
            header = read_csv_header(input_path)
            validate_expected_columns(header, args.expected_column)
        elif args.expected_column:
            raise ValueError("--expected-column requires a CSV --input file.")
        processed_directory = prepare_processed_directory(args.processed_dir)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Validated input: {input_path}")
    if header is not None:
        print(f"CSV columns inspected: {len(header)}")
    print(f"Processed directory ready: {processed_directory.resolve()}")
    print("No transformation or dataset copy was performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
