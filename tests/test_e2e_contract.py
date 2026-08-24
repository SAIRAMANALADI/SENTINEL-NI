"""End-to-end contract and graceful-error acceptance tests."""

from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest
import yaml

from src.forecasting.inference import predict_network_state_sequence


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "samples" / "inference_demo_sequence.csv"


def _sample() -> pd.DataFrame:
    return pd.read_csv(SAMPLE)


def test_e2e_output_contract() -> None:
    result = predict_network_state_sequence(_sample())
    assert result["model_version"]
    assert result["reference_timestamp"]
    assert result["forecast_horizon_seconds"] == 50
    assert len(result["forecast"]) == 5
    assert all({"step", "horizon_seconds", "timestamp", "score", "warning"} <= set(row) for row in result["forecast"])
    assert result["operating_mode"]
    assert 0 <= result["threshold"] <= 1
    assert {"top_features", "temporal_positions"} <= set(result["explanation"])


def test_missing_input_file_fails_clearly() -> None:
    with pytest.raises(FileNotFoundError):
        pd.read_csv(ROOT / "data" / "samples" / "missing.csv")


@pytest.mark.parametrize("mutation,match", [
    (lambda frame: frame.drop(columns=["flow_count"]), "missing"),
    (lambda frame: frame.head(9), "exactly 10"),
    (lambda frame: frame.assign(flow_count=frame["flow_count"].astype(float).mask([True] + [False] * 9)), "NaN or Inf"),
    (lambda frame: frame.assign(flow_count=frame["flow_count"].astype(float).map(lambda value: np.inf if value else value)), "NaN or Inf"),
])
def test_invalid_sequences_fail_without_model_execution(mutation, match: str) -> None:
    with pytest.raises((ValueError, TypeError), match=match):
        predict_network_state_sequence(mutation(_sample()))


def test_malformed_file_and_missing_runtime_artifacts_fail_gracefully(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.csv"
    malformed.write_text('"unclosed,field\n', encoding="utf-8")
    with pytest.raises(pd.errors.ParserError):
        pd.read_csv(malformed)

    sample = _sample()
    with pytest.raises(FileNotFoundError):
        predict_network_state_sequence(sample, checkpoint_path=tmp_path / "missing.pt")
    with pytest.raises(FileNotFoundError):
        predict_network_state_sequence(sample, policy_path=tmp_path / "missing.yaml")

    malformed_policy = tmp_path / "malformed.yaml"
    malformed_policy.write_text("modes: [", encoding="utf-8")
    with pytest.raises(yaml.YAMLError):
        predict_network_state_sequence(sample, policy_path=malformed_policy)


def test_cli_reports_input_errors_without_traceback(tmp_path: Path) -> None:
    missing = subprocess.run(
        [sys.executable, "run.py", "--input", str(tmp_path / "missing.csv")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert missing.returncode == 2
    assert "ERROR:" in missing.stderr
    assert "Traceback" not in missing.stderr

    malformed = tmp_path / "malformed.csv"
    malformed.write_text('"unclosed,field\n', encoding="utf-8")
    failed = subprocess.run(
        [sys.executable, "run.py", "--input", str(malformed)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert failed.returncode == 2
    assert "ERROR:" in failed.stderr
    assert "Traceback" not in failed.stderr
