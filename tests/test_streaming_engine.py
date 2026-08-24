"""Replay engine tests using deterministic mock inference."""

from pathlib import Path

import pandas as pd

from src.features.network_state import FEATURE_COLUMNS
from src.streaming.realtime_engine import RealtimeEngine
from src.streaming.replay import ReplayEvent, iter_replay_events
from src.streaming.state_aggregator import STATE_COLUMNS, aggregate_flow_window


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "samples" / "inference_demo_sequence.csv"


def _fake_inference(frame: pd.DataFrame) -> dict[str, object]:
    assert list(frame.columns) == STATE_COLUMNS
    assert len(frame) == 10
    return {
        "model_version": "mock",
        "forecast_horizon_seconds": 50,
        "forecast": [
            {"step": step, "horizon_seconds": step * 10, "score": 0.1, "warning": False}
            for step in range(1, 6)
        ],
        "explanation": {"top_features": [], "temporal_positions": []},
    }


def test_first_and_rolling_inference_triggers() -> None:
    engine = RealtimeEngine(inference_fn=_fake_inference)
    updates = list(engine.replay(iter_replay_events(SAMPLE)))
    assert len(updates) == 10
    assert sum(update.status == "inference_ready" for update in updates) == 1
    assert updates[-1].status == "inference_ready"
    assert updates[-1].inference_result is not None
    assert len(updates[-1].inference_result["forecast"]) == 5

    events = list(iter_replay_events(SAMPLE)) + [
        ReplayEvent(
            timestamp=pd.Timestamp("2018-02-22 01:01:40"),
            capture_day="2018-02-22",
            kind="state",
            payload={**list(iter_replay_events(SAMPLE))[-1].payload, "timestamp": pd.Timestamp("2018-02-22 01:01:40")},
        )
    ]
    rolling = list(RealtimeEngine(inference_fn=_fake_inference).replay(events))
    assert sum(update.status == "inference_ready" for update in rolling) == 2


def test_flow_window_uses_existing_aggregation_contract() -> None:
    rows = []
    for index in range(2):
        rows.append(
            {
                "timestamp_parsed": pd.Timestamp("2018-02-22 01:00:00") + pd.Timedelta(seconds=index),
                "capture_date": "2018-02-22",
                "Label": "Benign",
                "Dst Port": 443,
                "Flow Duration": 1000,
                "Tot Fwd Pkts": 2,
                "Tot Bwd Pkts": 1,
                "TotLen Fwd Pkts": 200,
                "TotLen Bwd Pkts": 100,
                "Flow IAT Mean": 10.0,
                "Flow IAT Std": 2.0,
                "SYN Flag Cnt": 1,
                "ACK Flag Cnt": 1,
                "RST Flag Cnt": 0,
                "Pkt Len Mean": 100.0,
                "Pkt Len Std": 5.0,
            }
        )
    state = aggregate_flow_window(rows)
    assert list(state.columns) == STATE_COLUMNS
    assert state.iloc[0]["flow_count"] == 2
    assert state.iloc[0]["packet_sum"] == 6
