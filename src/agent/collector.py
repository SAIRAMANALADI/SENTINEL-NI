"""Metadata-only packet collection and frozen 10-second state emission."""

from __future__ import annotations

from collections import defaultdict
from threading import RLock
from typing import Any, Callable

import pandas as pd

from src.streaming.flow_builder import FlowBuilder
from src.streaming.source_activity import SourceActivityAccumulator
from src.streaming.state_aggregator import build_network_state_for_inference


class AgentCollector:
    """Convert local packet events into approved states without retaining packets."""

    def __init__(
        self,
        *,
        interface: str,
        on_state: Callable[[dict[str, Any]], bool | None],
        on_source_activity: Callable[[pd.DataFrame], bool | None] | None = None,
    ) -> None:
        self.interface = interface
        self._on_state = on_state
        self._on_source_activity = on_source_activity
        self._builder = FlowBuilder()
        self._source_accumulator = SourceActivityAccumulator(interval_seconds=10) if on_source_activity else None
        self._windows: dict[pd.Timestamp, list[dict[str, Any]]] = defaultdict(list)
        self._lock = RLock()
        self._last_window: pd.Timestamp | None = None
        self._state_count = 0
        self._flow_count = 0
        self._error_count = 0

    def _emit_state(self, row: pd.Series) -> None:
        state = row.to_dict()
        state["timestamp"] = pd.Timestamp(state["timestamp"]).isoformat()
        state["capture_day"] = str(state["capture_day"])
        if self._on_state(state) is False:
            raise RuntimeError("agent state queue is full; state delivery was rejected")
        self._state_count += 1
        self._last_window = pd.Timestamp(row["timestamp"])

    def _pending_states(self) -> pd.DataFrame:
        flows = [flow for window_flows in self._windows.values() for flow in window_flows]
        if not flows:
            return pd.DataFrame()
        states, _ = build_network_state_for_inference(pd.DataFrame(flows), interval_seconds=10)
        return states

    def _emit_due(self, current_window: pd.Timestamp) -> None:
        states = self._pending_states()
        if states.empty:
            return
        timestamps = pd.to_datetime(states["timestamp"], errors="raise", format="mixed")
        for _, row in states.loc[timestamps < current_window].iterrows():
            self._emit_state(row)
        for window in [window for window in self._windows if window < current_window]:
            self._windows.pop(window)

    def _accept_flows(
        self,
        flows: list[dict[str, Any]],
        *,
        completion_timestamp: pd.Timestamp | None = None,
    ) -> None:
        for completed_flow in flows:
            # A flow may remain active for many intervals.  Its first packet is
            # retained for flow semantics, but live state scheduling must use
            # the completion watermark so a late completion cannot reopen an
            # already-emitted historical window.  The watermark is the current
            # packet's capture timestamp, never agent receive time.
            flow = dict(completed_flow)
            close_timestamp = (
                completion_timestamp
                if completion_timestamp is not None
                else pd.Timestamp(flow.get("last_packet_timestamp", flow["timestamp_parsed"]))
            )
            flow["timestamp_parsed"] = close_timestamp
            flow["capture_date"] = close_timestamp.strftime("%Y-%m-%d")
            window = close_timestamp.floor("10s")
            self._windows[window].append(flow)
            self._flow_count += 1

    def ingest_event(self, event: dict[str, Any]) -> bool:
        """Consume one packet event. Only completed flow fields enter memory."""

        with self._lock:
            try:
                if self._source_accumulator is not None:
                    completed_source_activity = self._source_accumulator.feed(event)
                    if completed_source_activity is not None and not completed_source_activity.empty:
                        if self._on_source_activity is not None and self._on_source_activity(completed_source_activity) is False:
                            raise RuntimeError("agent source activity queue is full; source delivery was rejected")
                flows = self._builder.feed_event(event)
                if flows:
                    completion_timestamp = pd.Timestamp(event["timestamp"])
                    self._accept_flows(flows, completion_timestamp=completion_timestamp)
                    newest = completion_timestamp.floor("10s")
                    self._emit_due(newest)
            except Exception:
                self._error_count += 1
                raise
        return True

    def flush(self) -> int:
        """Flush active flows and emit all remaining complete windows."""

        with self._lock:
            self._accept_flows(self._builder.flush())
            states = self._pending_states()
            for _, row in states.iterrows():
                if self._last_window is not None and pd.Timestamp(row["timestamp"]) <= self._last_window:
                    continue
                self._emit_state(row)
            self._windows.clear()
            if self._source_accumulator is not None:
                completed_source_activity = self._source_accumulator.flush()
                if completed_source_activity is not None and not completed_source_activity.empty:
                    if self._on_source_activity is not None and self._on_source_activity(completed_source_activity) is False:
                        raise RuntimeError("agent source activity queue is full; source delivery was rejected")
            return self._state_count

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "interface": self.interface,
                "pending_windows": len(self._windows),
                "states_emitted": self._state_count,
                "completed_flows": self._flow_count,
                "error_count": self._error_count,
                "last_state_timestamp": self._last_window.isoformat() if self._last_window is not None else None,
                "raw_packets_retained": False,
                "source_activity_enabled": self._source_accumulator is not None,
            }
