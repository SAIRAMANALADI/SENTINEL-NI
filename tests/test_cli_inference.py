"""CLI smoke test for a fresh Python-process inference run."""

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_cli_runs_and_writes_json(tmp_path: Path) -> None:
    output = tmp_path / "inference_result.json"
    completed = subprocess.run(
        [
            sys.executable,
            "run.py",
            "--input",
            "data/samples/inference_demo_sequence.csv",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "Predictive warning" in completed.stdout or "No predictive warning" in completed.stdout
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["operating_mode"] == "balanced"
    assert len(result["forecast"]) == 5
