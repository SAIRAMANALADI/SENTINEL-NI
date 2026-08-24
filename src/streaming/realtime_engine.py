"""Replay-to-inference engine using the existing inference API."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable

import pandas as pd

from src.evaluation.mitigation_policy import recommendations_for_sources
from src.forecasting.inference import predict_network_state_sequence
from src.streaming.replay import ReplayEvent
from src.streaming.state_aggregator import aggregate_flow_window, state_from_replay_event
from src.streaming.state_buffer import BufferUpdate, StateBuffer
from src.streaming.source_activity import SourceActivityAccumulator
from src.streaming.source_forecast import prioritize_sources


InferenceFunction = Callable[[pd.DataFrame], dict[str, Any]]


@dataclass(frozen=True)
class EngineUpdate:
    status: str
    state_index: int | None
    timestamp: str | None
    inference_result: dict[str, Any] | None = None
    processing_ms: float = 0.0
    reason: str | None = None
    source_activity: pd.DataFrame | None = None
    source_prioritization: pd.DataFrame | None = None
    mitigation_recommendations: list[dict[str, Any]] | None = None


class RealtimeEngine:
    """Consume states/events and trigger inference on every ready 10-state window."""

    def __init__(
        self,
        *,
        sequence_length: int = 10,
        interval_seconds: int = 10,
        inference_fn: InferenceFunction = predict_network_state_sequence,
        source_activity_enabled: bool = False,
    ) -> None:
        self.buffer = StateBuffer(sequence_length=sequence_length, interval_seconds=interval_seconds)
        self.interval_seconds = interval_seconds
        self.inference_fn = inference_fn
        self._pending_flow_events: list[dict[str, Any]] = []
        self._pending_flow_bucket: pd.Timestamp | None = None
        self._last_event_timestamp: pd.Timestamp | None = None
        self.source_activity_enabled = source_activity_enabled
        self._source_accumulator = SourceActivityAccumulator(interval_seconds) if source_activity_enabled else None
        self._latest_source_activity: pd.DataFrame | None = None

    def _source_update(self, activity: pd.DataFrame) -> EngineUpdate:
        prioritized = prioritize_sources(activity)
        recommendations = recommendations_for_sources(prioritized.to_dict(orient="records"))
        self._latest_source_activity = activity
        timestamp = activity["interval_end"].max().isoformat() if not activity.empty else None
        return EngineUpdate(
            status="source_activity_ready",
            state_index=None,
            timestamp=timestamp,
            source_activity=activity,
            source_prioritization=prioritized,
            mitigation_recommendations=recommendations,
        )

    def _consume_state(self, state: pd.DataFrame) -> EngineUpdate:
        buffer_update: BufferUpdate = self.buffer.push(state)
        if buffer_update.status != "ready" or buffer_update.sequence is None:
            return EngineUpdate(
                status=buffer_update.status,
                state_index=buffer_update.state_index,
                timestamp=buffer_update.timestamp,
                reason=buffer_update.reason,
            )
        started = time.perf_counter()
        result = dict(self.inference_fn(buffer_update.sequence))
        processing_ms = (time.perf_counter() - started) * 1000
        result["current_timestamp"] = buffer_update.timestamp
        result["state_index"] = buffer_update.state_index
        result["input_states"] = len(buffer_update.sequence)
        result["processing_ms"] = processing_ms
        if self._latest_source_activity is not None:
            prioritized = prioritize_sources(self._latest_source_activity, result)
            result["source_prioritization"] = prioritized.to_dict(orient="records")
            result["source_mitigation"] = recommendations_for_sources(result["source_prioritization"])
        return EngineUpdate(
            status="inference_ready",
            state_index=buffer_update.state_index,
            timestamp=buffer_update.timestamp,
            inference_result=result,
            processing_ms=processing_ms,
        )

    def _flush_flow_window(self) -> EngineUpdate | None:
        if not self._pending_flow_events:
            return None
        state = aggregate_flow_window(self._pending_flow_events, interval_seconds=self.interval_seconds)
        self._pending_flow_events = []
        self._pending_flow_bucket = None
        return self._consume_state(state)

    def feed_event(self, event: ReplayEvent) -> list[EngineUpdate]:
        """Feed one event and return zero or more state/inference updates."""

        if self._last_event_timestamp is not None:
            if event.timestamp < self._last_event_timestamp:
                raise ValueError("replay events must be chronologically ordered")
            if event.kind == "state" and event.timestamp == self._last_event_timestamp:
                raise ValueError("replay state events must have unique timestamps")
        self._last_event_timestamp = event.timestamp

        if event.kind == "state":
            pending = self._flush_flow_window()
            updates = [pending] if pending is not None else []
            updates.append(self._consume_state(state_from_replay_event(event.__dict__)))
            return updates
        if event.kind == "packet":
            if self._source_accumulator is None:
                raise ValueError("packet replay events require source_activity_enabled=True")
            completed = self._source_accumulator.feed(event.payload)
            return [self._source_update(completed)] if completed is not None else []
        if event.kind != "flow":
            raise ValueError(f"unsupported replay event kind: {event.kind}")

        bucket = event.timestamp.floor(f"{self.interval_seconds}s")
        if self._pending_flow_bucket is None:
            self._pending_flow_bucket = bucket
        elif bucket != self._pending_flow_bucket:
            pending = self._flush_flow_window()
            updates = [pending] if pending is not None else []
            self._pending_flow_bucket = bucket
            self._pending_flow_events.append(event.payload)
            return updates
        self._pending_flow_events.append(event.payload)
        return []

    def finish(self) -> list[EngineUpdate]:
        updates: list[EngineUpdate] = []
        if self._source_accumulator is not None:
            completed = self._source_accumulator.flush()
            if completed is not None:
                updates.append(self._source_update(completed))
        pending = self._flush_flow_window()
        if pending is not None:
            updates.append(pending)
        return updates

    def replay(self, events: Iterable[ReplayEvent], max_states: int | None = None) -> Iterable[EngineUpdate]:
        emitted_states = 0
        for event in events:
            for update in self.feed_event(event):
                is_state_update = update.status != "source_activity_ready"
                if is_state_update:
                    emitted_states += 1
                yield update
                if max_states is not None and is_state_update and emitted_states >= max_states:
                    return
        for update in self.finish():
            yield update
            is_state_update = update.status != "source_activity_ready"
            if is_state_update:
                emitted_states += 1
            if max_states is not None and is_state_update and emitted_states >= max_states:
                return
