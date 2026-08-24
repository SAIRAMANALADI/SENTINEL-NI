"""Deterministic replay-source tests."""

from pathlib import Path

import pandas as pd
import pytest

from src.streaming.replay import iter_replay_events
from src.streaming.state_aggregator import STATE_COLUMNS


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "samples" / "inference_demo_sequence.csv"
STATE_DATASET = ROOT / "data" / "processed" / "cic_ids2018_network_states.parquet"


def test_replay_preserves_sample_timestamps_and_order() -> None:
    events = list(iter_replay_events(SAMPLE))
    assert len(events) == 10
    assert all(event.kind == "state" for event in events)
    assert events[0].timestamp == pd.Timestamp("2018-02-22 01:00:00")
    assert events[-1].timestamp == pd.Timestamp("2018-02-22 01:01:30")
    assert all((right.timestamp - left.timestamp) == pd.Timedelta(seconds=10) for left, right in zip(events, events[1:]))


def test_replay_reads_approved_state_parquet_without_targets() -> None:
    events = list(iter_replay_events(STATE_DATASET, max_events=3))
    assert len(events) == 3
    assert set(events[0].payload) == set(STATE_COLUMNS)
    assert "future_attack_state" not in events[0].payload


def test_replay_rejects_missing_source() -> None:
    with pytest.raises(FileNotFoundError):
        list(iter_replay_events(ROOT / "data" / "samples" / "does-not-exist.csv"))
