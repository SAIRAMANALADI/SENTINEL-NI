"""Strict rolling buffer for validated 10-second network states."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.streaming.state_aggregator import STATE_COLUMNS, validate_state


class StateBufferError(ValueError):
    """Raised when a state violates a hard ordering or schema invariant."""


@dataclass(frozen=True)
class BufferUpdate:
    status: str
    state_index: int | None
    timestamp: str | None
    sequence: pd.DataFrame | None = None
    reason: str | None = None


class StateBuffer:
    """Keep the last L states without interpolating missing intervals."""

    def __init__(self, sequence_length: int = 10, interval_seconds: int = 10) -> None:
        if isinstance(sequence_length, bool) or not isinstance(sequence_length, int) or sequence_length < 1:
            raise ValueError("sequence_length must be a positive integer")
        if isinstance(interval_seconds, bool) or not isinstance(interval_seconds, int) or interval_seconds != 10:
            raise ValueError("interval_seconds must be exactly 10")
        self.sequence_length = sequence_length
        self.interval_seconds = interval_seconds
        self._states: list[pd.DataFrame] = []
        self._accepted_count = 0
        self._capture_day: str | None = None

    @property
    def accepted_count(self) -> int:
        return self._accepted_count

    @property
    def capture_day(self) -> str | None:
        return self._capture_day

    def reset(self) -> None:
        self._states.clear()
        self._capture_day = None

    def push(self, state: pd.DataFrame | pd.Series | dict[str, object]) -> BufferUpdate:
        validated = validate_state(state)
        if len(validated) != 1:
            raise StateBufferError("StateBuffer.push accepts exactly one state")
        row = validated.iloc[[0]].copy()
        timestamp = pd.Timestamp(row["timestamp"].iloc[0])
        capture_day = str(row["capture_day"].iloc[0])

        if self._states and capture_day != self._capture_day:
            previous = pd.Timestamp(self._states[-1]["timestamp"].iloc[0])
            if timestamp <= previous:
                raise StateBufferError("capture-day boundary must advance chronologically")
            self.reset()
            self._capture_day = capture_day
            self._states.append(row)
            self._accepted_count += 1
            return BufferUpdate(
                status="day_boundary_reset",
                state_index=self._accepted_count - 1,
                timestamp=timestamp.isoformat(),
                reason="capture_day changed; no cross-day sequence was formed",
            )

        if self._states:
            previous = pd.Timestamp(self._states[-1]["timestamp"].iloc[0])
            delta = timestamp - previous
            if delta == pd.Timedelta(0):
                raise StateBufferError("duplicate state timestamp")
            if delta < pd.Timedelta(0):
                raise StateBufferError("out-of-order state timestamp")
            expected = pd.Timedelta(seconds=self.interval_seconds)
            if delta != expected:
                return BufferUpdate(
                    status="waiting_for_next_valid_state",
                    state_index=None,
                    timestamp=timestamp.isoformat(),
                    reason=(
                        f"received {delta.total_seconds():g}s after the previous state; "
                        f"expected exactly {self.interval_seconds}s; no state was interpolated"
                    ),
                )
        else:
            self._capture_day = capture_day

        self._states.append(row)
        self._accepted_count += 1
        if len(self._states) > self.sequence_length:
            self._states.pop(0)
        sequence = None
        status = "buffering"
        if len(self._states) == self.sequence_length:
            status = "ready"
            sequence = pd.concat(self._states, ignore_index=True)[STATE_COLUMNS]
        return BufferUpdate(
            status=status,
            state_index=self._accepted_count - 1,
            timestamp=timestamp.isoformat(),
            sequence=sequence,
        )
