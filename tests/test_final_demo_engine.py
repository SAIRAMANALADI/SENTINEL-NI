"""Integration tests for the final offline demonstration engine."""

import json
from pathlib import Path

from src.streaming.final_demo_engine import assert_json_serializable, load_demo_events, run_final_demo


ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "data" / "samples" / "final_demo_events.csv"


def test_final_demo_loads_marked_events_and_runs_real_forecast() -> None:
    events = load_demo_events(DEMO)
    result = run_final_demo(DEMO)
    assert len(events) == 86
    assert result["state_count"] == 10
    assert result["history_length"] == 10
    assert len(result["network_forecast"]["forecasts"]) == 5
    assert all(0.0 <= row["score"] <= 1.0 for row in result["network_forecast"]["forecasts"])
    assert result["network_forecast"]["threshold"] == 0.19
    assert {row["source_ip"] for row in result["source_priorities"]} == {"10.0.0.1", "10.0.0.2", "10.0.0.3"}
    assert all(row["risk_status"] == "candidate source" for row in result["source_priorities"])
    assert all(row["automatic_block"] is False for row in result["mitigation_recommendations"])
    assert result["simulation_only"] is True
    assert result["pcap_attribution_validated"] is False


def test_final_demo_result_is_json_serializable_and_deterministic_structure() -> None:
    first = run_final_demo(DEMO)
    second = run_final_demo(DEMO)
    assert_json_serializable(first)
    json.dumps(first, allow_nan=False)
    assert first.keys() == second.keys()
    assert [row["step"] for row in first["network_forecast"]["forecasts"]] == [1, 2, 3, 4, 5]
    assert all("attacker" not in json.dumps(row).lower() for row in first["source_priorities"])
    assert all("attacker" not in json.dumps(row).lower() for row in first["mitigation_recommendations"])
