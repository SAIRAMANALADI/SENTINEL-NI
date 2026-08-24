"""Tests for recommendation-only mitigation policy."""

import pytest

from src.evaluation.mitigation_policy import recommend_mitigation


@pytest.mark.parametrize(
    ("priority", "recommendation"),
    [
        ("LOW PRIORITY SOURCE", "Monitor source"),
        ("MEDIUM PRIORITY SOURCE", "Consider temporary rate limiting"),
        ("HIGH PRIORITY SOURCE", "Consider aggressive rate limiting / investigation"),
    ],
)
def test_policy_recommendations_are_explicit_and_non_blocking(priority: str, recommendation: str) -> None:
    result = recommend_mitigation(priority, source_ip="10.0.0.1", priority_points=4)
    assert result["recommendation"] == recommendation
    assert result["risk_status"] == "candidate source"
    assert result["automatic_block"] is False
    assert "attacker" not in result["recommendation"].lower()


def test_unknown_priority_is_rejected() -> None:
    with pytest.raises(ValueError):
        recommend_mitigation("CONFIRMED ATTACKER")
