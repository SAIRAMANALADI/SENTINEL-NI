"""Small in-process metrics registry suitable for local MVP observability."""

from __future__ import annotations

import threading
from collections import defaultdict
from typing import Any


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: defaultdict[str, int] = defaultdict(int)
        self._latencies: dict[str, dict[str, float | int | None]] = {}

    def increment(self, name: str, value: int = 1) -> None:
        with self._lock:
            self._counters[name] += int(value)

    def observe(self, name: str, milliseconds: float) -> None:
        with self._lock:
            value = float(milliseconds)
            stats = self._latencies.setdefault(
                name,
                {"count": 0, "total_ms": 0.0, "last_ms": None},
            )
            stats["count"] = int(stats["count"]) + 1
            stats["total_ms"] = float(stats["total_ms"]) + value
            stats["last_ms"] = value

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            latencies = {
                name: {
                    "count": int(values["count"]),
                    "last_ms": values["last_ms"],
                    "mean_ms": (
                        float(values["total_ms"]) / int(values["count"])
                        if int(values["count"])
                        else None
                    ),
                }
                for name, values in self._latencies.items()
            }
            return {"counters": dict(self._counters), "latencies": latencies}
