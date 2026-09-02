"""Named common collector contract used by all telemetry sources."""

from src.telemetry.base import TelemetryAdapter


Collector = TelemetryAdapter

__all__ = ["Collector"]
