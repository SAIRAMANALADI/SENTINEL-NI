"""Tests for optional source events in the existing replay engine."""

from pathlib import Path

from src.streaming.realtime_engine import RealtimeEngine
from src.streaming.replay import iter_packet_replay_events


ROOT = Path(__file__).resolve().parents[1]
MOCK = ROOT / "data" / "samples" / "source_attribution_mock.jsonl"


def test_source_enabled_replay_emits_source_updates_without_model_changes() -> None:
    engine = RealtimeEngine(source_activity_enabled=True)
    updates = list(engine.replay(iter_packet_replay_events(MOCK)))
    source_updates = [update for update in updates if update.status == "source_activity_ready"]
    assert len(source_updates) == 4
    assert source_updates[-1].source_activity is not None
    assert source_updates[-1].source_prioritization is not None
    assert all(update.mitigation_recommendations is not None for update in source_updates)
