"""Tests for deterministic offline rate-limit simulation."""

import pytest

from src.evaluation.rate_limit_simulator import simulate_rate_limit


def test_rate_limit_simulation_matches_documented_example() -> None:
    result = simulate_rate_limit("10.0.0.3", 350, 50)
    assert result["original_traffic_rate"] == 350.0
    assert result["simulated_allowed_rate"] == 50.0
    assert result["throttled_amount"] == 300.0
    assert result["percentage_reduction"] == pytest.approx(85.7142857)
    assert result["offline_only"] is True
    assert result["firewall_changed"] is False


@pytest.mark.parametrize("current,limit", [(-1, 50), (100, -1), (float("inf"), 50)])
def test_invalid_rates_are_rejected(current: float, limit: float) -> None:
    with pytest.raises(ValueError):
        simulate_rate_limit("10.0.0.1", current, limit)
