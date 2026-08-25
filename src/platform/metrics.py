"""Small in-process metrics registry suitable for local MVP observability."""

from __future__ import annotations

import threading
from collections import defaultdict
from typing import Any


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: defaultdict[str, int] = defaultdict(int)
        self._latencies: defaultdict[str, list[float]] = defaultdict(list)

    def increment(self, name: str, value: int = 1) -> None:
        with self._lock:
            self._counters[name] += int(value)

    def observe(self, name: str, milliseconds: float) -> None:
        with self._lock:
            self._latencies[name].append(float(milliseconds))

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            latencies = {
                name: {
                    "count": len(values),
                    "last_ms": values[-1] if values else None,
                    "mean_ms": sum(values) / len(values) if values else None,
                }
                for name, values in self._latencies.items()
            }
            return {"counters": dict(self._counters), "latencies": latencies}

