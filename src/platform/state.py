"""Explicit service states used by health, readiness, and degraded responses."""

from enum import StrEnum


class ServiceState(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    DATA_STALE = "DATA_STALE"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    TELEMETRY_UNAVAILABLE = "TELEMETRY_UNAVAILABLE"

