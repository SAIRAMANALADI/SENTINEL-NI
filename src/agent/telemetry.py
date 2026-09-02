"""Versioned batching for state-only remote sensor telemetry."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
import re
from typing import Any


SENSOR_ID_PATTERN = re.compile(r"^sensor-[a-f0-9]{16}$")
MAX_BATCH_STATES = 60


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TelemetryBatcher:
    """Build bounded, monotonic, state-only telemetry envelopes.

    The caller owns the bounded queue of completed states.  This class owns
    envelope construction and sequence assignment, so every payload sent by
    an agent has one sensor identity and one persistent sequence number.
    """

    def __init__(
        self,
        sensor_id: str,
        *,
        sequence_start: int = 1,
        batch_size: int = 6,
        clock: Callable[[], datetime] = _utc_now,
        on_sequence_advanced: Callable[[int], None] | None = None,
    ) -> None:
        if not SENSOR_ID_PATTERN.fullmatch(sensor_id):
            raise ValueError("sensor_id does not match the registered sensor format")
        if isinstance(sequence_start, bool) or sequence_start < 1:
            raise ValueError("sequence_start must be positive")
        if isinstance(batch_size, bool) or not 1 <= batch_size <= MAX_BATCH_STATES:
            raise ValueError(f"batch_size must be between 1 and {MAX_BATCH_STATES}")
        self.sensor_id = sensor_id
        self._next_sequence = int(sequence_start)
        self.batch_size = int(batch_size)
        self._clock = clock
        self._on_sequence_advanced = on_sequence_advanced
        self._pending: deque[Mapping[str, Any]] = deque(maxlen=self.batch_size)

    @property
    def next_sequence(self) -> int:
        return self._next_sequence

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    def add(self, state: Mapping[str, Any]) -> dict[str, Any] | None:
        """Collect one state and emit a payload when the batch is full."""

        if not isinstance(state, Mapping):
            raise ValueError("telemetry state must be a mapping")
        self._pending.append(state)
        if len(self._pending) < self.batch_size:
            return None
        states = list(self._pending)
        self._pending.clear()
        return self.build(states)

    def flush(self) -> dict[str, Any] | None:
        """Emit a bounded partial batch, if one is pending."""

        if not self._pending:
            return None
        states = list(self._pending)
        self._pending.clear()
        return self.build(states)

    def build(self, states: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        """Build one payload without altering state order or feature values."""

        if not states:
            raise ValueError("telemetry batch must contain at least one state")
        if len(states) > self.batch_size or len(states) > MAX_BATCH_STATES:
            raise ValueError("telemetry batch exceeds the configured batch size")
        if any(not isinstance(state, Mapping) for state in states):
            raise ValueError("telemetry states must be mappings")
        copied_states = [dict(state) for state in states]
        sent_at = self._clock()
        if sent_at.tzinfo is None or sent_at.utcoffset() is None:
            raise ValueError("telemetry clock must return a timezone-aware datetime")
        sequence = self._next_sequence
        payload = {
            "schema_version": "1",
            "sensor_id": self.sensor_id,
            "sequence": sequence,
            "sent_at": sent_at.astimezone(timezone.utc).isoformat(),
            "states": copied_states,
        }
        self._next_sequence += 1
        if self._on_sequence_advanced is not None:
            self._on_sequence_advanced(self._next_sequence)
        return payload
