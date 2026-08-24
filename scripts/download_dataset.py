"""Validate an explicitly supplied dataset source without downloading data.

The foundation phase must not perform implicit network downloads. This helper
accepts a local file or directory, validates optional expected paths, and
creates the raw-data directory. It does not copy or embed dataset contents.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def validate_source(source: Path) -> Path:
    """Return an existing local source or raise a clear error."""
    raw_source = str(source).strip()
    if raw_source.lower().startswith(("http://", "https://")):
        raise ValueError("Remote URLs are disabled; provide an explicit local source path.")
    source = source.expanduser().resolve()
    if not source.exists():
        raise FileNotFoundError(f"Dataset source does not exist: {source}")
    return source


def validate_expected_paths(source: Path, expected_paths: list[str]) -> list[Path]:
    """Validate paths relative to a directory or the parent of a source file."""
    base = source if source.is_dir() else source.parent
    missing = [value for value in expected_paths if not (base / value).exists()]
    if missing:
        raise FileNotFoundError(
            "Required dataset paths are missing relative to "
            f"{base}: {', '.join(missing)}"
        )
    return [base / value for value in expected_paths]


def prepare_raw_directory(raw_directory: Path) -> Path:
    """Create and return the repository raw-data directory."""
    raw_directory.mkdir(parents=True, exist_ok=True)
    return raw_directory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a local dataset source without downloading or copying it."
    )
    parser.add_argument(
        "--source",
        required=True,
        type=Path,
        help="Explicit local dataset file or directory.",
    )
    parser.add_argument(
        "--expected",
        action="append",
        default=[],
        help="Expected file/directory relative to --source; repeat as needed.",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "raw",
        help="Repository raw-data directory to create.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        source = validate_source(args.source)
        expected = validate_expected_paths(source, args.expected)
        raw_directory = prepare_raw_directory(args.raw_dir)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Validated local source: {source}")
    print(f"Validated expected paths: {len(expected)}")
    print(f"Raw directory ready: {raw_directory.resolve()}")
    print("No data was downloaded or copied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
