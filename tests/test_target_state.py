from __future__ import annotations

import pandas as pd

from src.features.network_state import aggregate_network_states
from tests.test_network_state import _flows


def test_future_target_is_next_interval_within_day() -> None:
    states, _ = aggregate_network_states(_flows(), interval_seconds=10)
    first_day = states[states["capture_day"] == "2018-02-14"]
    assert first_day["binary_attack_state"].tolist() == [0, 1]
    assert first_day["future_attack_state"].tolist() == [1, -1]
    assert first_day["future_target_available"].tolist() == [True, False]


def test_non_benign_labels_are_target_metadata_not_features() -> None:
    states, _ = aggregate_network_states(_flows(), interval_seconds=10)
    assert states.loc[states["capture_day"] == "2018-02-14", "malicious_flow_count"].tolist() == [0, 1]
    assert "Label" not in states.columns
    assert "binary_attack_state" not in ["flow_count", "byte_sum", "packet_sum"]
