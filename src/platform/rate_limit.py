"""Small process-local sliding-window limiters for control-plane protection."""

from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Callable


class RateLimitExceeded(ValueError):
    """The caller exceeded a configured process-local request class limit."""


class SlidingWindowRateLimiter:
    def __init__(self, limit_per_minute: int, *, clock: Callable[[], datetime] | None = None) -> None:
        if limit_per_minute <= 0:
            raise ValueError("rate limit must be positive")
        self.limit_per_minute = limit_per_minute
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._history: dict[str, deque[datetime]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> None:
        now = self._clock()
        cutoff = now - timedelta(minutes=1)
        with self._lock:
            history = self._history[key]
            while history and history[0] < cutoff:
                history.popleft()
            if len(history) >= self.limit_per_minute:
                raise RateLimitExceeded("request rate limit exceeded")
            history.append(now)
