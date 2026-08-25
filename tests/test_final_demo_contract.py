"""Contract tests for final demo documentation and UI boundaries."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_final_demo_contract_and_runbook_exist() -> None:
    contract = (ROOT / "docs/FINAL_INTEGRATION_CONTRACT.md").read_text(encoding="utf-8")
    assert "EVENT" in contract
    assert "SOURCE ACTIVITY" in contract
    assert "EXISTING K=5 INFERENCE" in contract
    assert "simulation_only=true" in contract

    architecture = (ROOT / "docs/FINAL_DEMO_ARCHITECTURE.md").read_text(encoding="utf-8")
    runbook = (ROOT / "docs/FINAL_DEMO_RUNBOOK.md").read_text(encoding="utf-8")
    assert "RUN FULL DEMO" in architecture
    assert "do not say attacker detected" in runbook.lower()
    assert "90–120" in runbook


def test_streamlit_exposes_three_modes_and_full_demo_button() -> None:
    source = (ROOT / "app/streamlit_app.py").read_text(encoding="utf-8")
    assert "Full Integrated Demo" in source
    assert "RUN FULL DEMO" in source
    assert "run_final_demo" in source
