"""Prepare or run a target-approved, capture-day-aware Logistic Regression baseline.

The command intentionally stops before reading/training when the approved
multi-day target specification is absent. No target mapping is inferred.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.preprocessing.multiday_baseline import target_spec_status


DEFAULT_INPUT = PROJECT_ROOT / "data" / "processed" / "cic_ids2018_multiday_flow.parquet"
DEFAULT_TARGET_SPEC = PROJECT_ROOT / "docs" / "TARGET_STATE_SPEC.md"
DEFAULT_SPLIT_REPORT = PROJECT_ROOT / "results" / "multiday_split_report.json"
DEFAULT_REPORT = PROJECT_ROOT / "results" / "MULTIDAY_BASELINE_REPORT.md"


def write_blocked_report(
    report_path: Path,
    input_path: Path,
    target_spec_path: Path,
    split_report_path: Path,
    target_status: dict[str, Any],
) -> dict[str, Any]:
    split = json.loads(split_report_path.read_text(encoding="utf-8"))
    result = {
        "status": "TARGET_SPECIFICATION_REQUIRED",
        "input_path": str(input_path.resolve()),
        "target_specification": target_status,
        "split_report": split,
        "training_executed": False,
        "metrics": None,
        "model_artifacts": [],
        "reason": "The expanded dataset has multiple source attack labels and no approved multi-day target rule. Training would require an invented label mapping.",
    }
    report = f"""# Multi-day Logistic Regression Baseline

## Status

**TARGET SPECIFICATION REQUIRED — TRAINING NOT EXECUTED**

The existing single-day target document, `docs/TARGET_DEFINITION.md`, only specifies `Benign -> 0` and `Infilteration -> 1`. It does not approve a target rule for the expanded source labels: FTP/SSH brute force, DDoS, web attacks, and infiltration. The required multi-day target specification `{target_spec_path}` is not available or not explicitly approved.

No target mapping was inferred. No preprocessing was fit, no Logistic Regression model was trained, and no precision, recall, F1, PR-AUC, false-positive rate, or confusion-matrix metrics were fabricated.

## Prepared day-aware split

The existing complete-day split is retained:

- Train days: `{split['train_days']}`
- Validation days: `{split['validation_days']}`
- Test days: `{split['test_days']}`
- Random row split: `false`
- Split report: `{split_report_path.resolve()}`

The split is scenario/day-aware and keeps entire capture days together. `source_file` and `capture_date` are provenance metadata and must not be used as model features.

## Prepared training framework

`src/preprocessing/multiday_baseline.py` provides:

- approved-target availability gating;
- complete capture-day split assignment;
- target/provenance exclusion;
- finite numeric feature validation; and
- explicit positive-label target construction that rejects unaccounted source labels.

Entry point: `{Path(__file__).resolve()}`

## Required next input

Developer 2 must finalize and explicitly approve a target specification that states:

1. the prediction time unit and whether this is current-state or future-state;
2. the positive source labels;
3. the treatment of every other observed source label;
4. whether `Benign` is the only negative class; and
5. the target alignment and anomaly policy.

After that document is approved, rerun the entry point against `{input_path.resolve()}`. Only then may preprocessing, Logistic Regression fitting, and requested metrics be produced.
"""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    return result


def prepare_or_train(
    input_path: Path = DEFAULT_INPUT,
    target_spec_path: Path = DEFAULT_TARGET_SPEC,
    split_report_path: Path = DEFAULT_SPLIT_REPORT,
    report_path: Path = DEFAULT_REPORT,
) -> dict[str, Any]:
    input_path = input_path.expanduser().resolve()
    if not input_path.is_file():
        raise FileNotFoundError(f"Multi-day Parquet does not exist: {input_path}")
    target_status = target_spec_status(target_spec_path)
    if not target_status["available"]:
        return write_blocked_report(
            report_path,
            input_path,
            target_spec_path.expanduser().resolve(),
            split_report_path.expanduser().resolve(),
            target_status,
        )
    raise NotImplementedError(
        "Approved target found, but target-specific training wiring must be reviewed before execution."
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--target-spec", type=Path, default=DEFAULT_TARGET_SPEC)
    parser.add_argument("--split-report", type=Path, default=DEFAULT_SPLIT_REPORT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = prepare_or_train(args.input, args.target_spec, args.split_report, args.report)
    except (FileNotFoundError, ValueError, TypeError, NotImplementedError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Status: {result['status']}")
    print(f"Training executed: {result['training_executed']}")
    print(f"Report: {args.report.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
