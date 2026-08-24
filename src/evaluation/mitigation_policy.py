"""Recommendation-only mitigation policy for candidate sources."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


RECOMMENDATIONS = {
    "LOW PRIORITY SOURCE": "Monitor source",
    "MEDIUM PRIORITY SOURCE": "Consider temporary rate limiting",
    "HIGH PRIORITY SOURCE": "Consider aggressive rate limiting / investigation",
}


def recommend_mitigation(
    priority: str,
    *,
    source_ip: str | None = None,
    priority_points: int | None = None,
) -> dict[str, Any]:
    """Return a deterministic recommendation; never block or label malicious."""

    normalized = str(priority).upper()
    if normalized not in RECOMMENDATIONS:
        raise ValueError(f"unsupported source priority: {priority!r}")
    result: dict[str, Any] = {
        "source_ip": source_ip,
        "priority": normalized,
        "recommendation": RECOMMENDATIONS[normalized],
        "risk_status": "candidate source",
        "automatic_block": False,
    }
    if priority_points is not None:
        result["priority_points"] = int(priority_points)
    return result


def recommendations_for_sources(rows: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        recommend_mitigation(
            str(row["priority"]),
            source_ip=str(row["source_ip"]),
            priority_points=int(row["priority_points"]),
        )
        for row in rows
    ]
