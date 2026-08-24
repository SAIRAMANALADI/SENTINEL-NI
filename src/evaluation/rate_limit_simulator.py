"""Offline deterministic rate-limit simulation."""

from __future__ import annotations

import math
from typing import Any


def simulate_rate_limit(source_ip: str, current_rate: float, recommended_limit: float) -> dict[str, Any]:
    """Simulate a rate limit without touching firewall or network state."""

    current = float(current_rate)
    limit = float(recommended_limit)
    if not math.isfinite(current) or not math.isfinite(limit):
        raise ValueError("traffic rates must be finite")
    if current < 0 or limit < 0:
        raise ValueError("traffic rates must be non-negative")
    allowed = min(current, limit)
    throttled = current - allowed
    reduction = (throttled / current * 100.0) if current else 0.0
    return {
        "source_ip": str(source_ip),
        "original_traffic_rate": current,
        "recommended_limit": limit,
        "simulated_allowed_rate": allowed,
        "throttled_amount": throttled,
        "percentage_reduction": reduction,
        "offline_only": True,
        "firewall_changed": False,
    }
