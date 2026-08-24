from __future__ import annotations

import numpy as np
import pandas as pd

from src.features.network_state import FEATURE_COLUMNS, aggregate_network_states


def _flows() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "capture_date": ["2018-02-14", "2018-02-14", "2018-02-15", "2018-02-15"],
            "timestamp_parsed": pd.to_datetime(
                ["2018-02-14 00:00:01", "2018-02-14 00:00:11", "2018-02-15 00:00:01", "2018-02-15 00:00:11"]
            ),
            "Label": ["Benign", "Attack", "Benign", "Benign"],
            "Dst Port": [80, 443, 53, 53],
            "Flow Duration": [10, 20, 30, 40],
            "Tot Fwd Pkts": [2, 4, 1, 1],
            "Tot Bwd Pkts": [1, 2, 1, 1],
            "TotLen Fwd Pkts": [100, 200, 20, 20],
            "TotLen Bwd Pkts": [50, 100, 20, 20],
            "Flow IAT Mean": [1, 2, 3, 4],
            "Flow IAT Std": [0, 1, 1, 1],
            "SYN Flag Cnt": [1, 0, 0, 0],
            "ACK Flag Cnt": [1, 1, 1, 1],
            "RST Flag Cnt": [0, 1, 0, 0],
            "Pkt Len Mean": [50, 100, 20, 20],
            "Pkt Len Std": [5, 10, 2, 2],
            "timestamp_capture_date_mismatch": [False, False, False, False],
        }
    )


def test_aggregation_is_deterministic_and_day_isolated() -> None:
    first, first_report = aggregate_network_states(_flows(), interval_seconds=10)
    second, second_report = aggregate_network_states(_flows(), interval_seconds=10)
    pd.testing.assert_frame_equal(first, second)
    assert first_report == second_report
    assert first["capture_day"].tolist() == ["2018-02-14", "2018-02-14", "2018-02-15", "2018-02-15"]
    assert first.groupby("capture_day").size().to_dict() == {"2018-02-14": 2, "2018-02-15": 2}
    assert first.loc[(first.capture_day == "2018-02-14") & (first.timestamp.dt.second == 10), "binary_attack_state"].item() == 1


def test_empty_state_is_zero_and_inputs_are_finite() -> None:
    states, _ = aggregate_network_states(_flows(), interval_seconds=5)
    assert (states["flow_count"] == 0).any()
    assert np.isfinite(states[FEATURE_COLUMNS].to_numpy(dtype="float64")).all()
    assert not {"Label", "original_label", "binary_label"}.intersection(states.columns)


def test_anomaly_is_excluded_without_guessing() -> None:
    frame = _flows()
    frame.loc[0, "timestamp_capture_date_mismatch"] = True
    states, report = aggregate_network_states(frame, interval_seconds=10)
    assert report["excluded_timestamp_anomalies"] == 1
    assert int(states["flow_count"].sum()) == 3
