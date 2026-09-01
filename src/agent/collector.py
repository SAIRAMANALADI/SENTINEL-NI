"""Metadata-only packet collection and frozen 10-second state emission."""

from __future__ import annotations

from collections import defaultdict
from threading import RLock
from typing import Any, Callable

import pandas as pd

from src.streaming.flow_builder import FlowBuilder
from src.streaming.state_aggregator import aggregate_flow_window


class AgentCollector:
    """Convert local packet events into approved states without retaining packets."""

    def __init__(self, *, interface: str, on_state: Callable[[dict[str, Any]], bool | None]) -> None:
        self.interface = interface
        self._on_state = on_state
        self._builder = FlowBuilder()
        self._windows: dict[pd.Timestamp, list[dict[str, Any]]] = defaultdict(list)
        self._lock = RLock()
        self._last_window: pd.Timestamp | None = None
        self._state_count = 0
        self._flow_count = 0
        self._error_count = 0

    def _emit_due(self, current_window: pd.Timestamp) -> None:
        due = sorted(window for window in self._windows if window < current_window)
        for window in due:
            flows = self._windows.pop(window)
            state = aggregate_flow_window(flows).iloc[0].to_dict()
            state["timestamp"] = pd.Timestamp(state["timestamp"]).isoformat()
            state["capture_day"] = str(state["capture_day"])
            if self._on_state(state) is False:
                raise RuntimeError("agent state queue is full; state delivery was rejected")
            self._state_count += 1
            self._last_window = window

    def _accept_flows(self, flows: list[dict[str, Any]]) -> None:
        for flow in flows:
            window = pd.Timestamp(flow["timestamp_parsed"]).floor("10s")
            self._windows[window].append(flow)
            self._flow_count += 1

    def ingest_event(self, event: dict[str, Any]) -> bool:
        """Consume one packet event. Only completed flow fields enter memory."""

        with self._lock:
            try:
                flows = self._builder.feed_event(event)
                if flows:
                    self._accept_flows(flows)
                    newest = max(pd.Timestamp(flow["timestamp_parsed"]).floor("10s") for flow in flows)
                    self._emit_due(newest)
            except Exception:
                self._error_count += 1
                raise
        return True

    def flush(self) -> int:
        """Flush active flows and emit all remaining complete windows."""

        with self._lock:
            self._accept_flows(self._builder.flush())
            for window in sorted(self._windows):
                flows = self._windows.pop(window)
                state = aggregate_flow_window(flows).iloc[0].to_dict()
                state["timestamp"] = pd.Timestamp(state["timestamp"]).isoformat()
                state["capture_day"] = str(state["capture_day"])
                if self._on_state(state) is False:
                    raise RuntimeError("agent state queue is full; state delivery was rejected")
                self._state_count += 1
                self._last_window = window
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
            }
