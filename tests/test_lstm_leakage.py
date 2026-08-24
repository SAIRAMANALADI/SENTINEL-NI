from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from src.forecasting.windowing import build_sequences
from src.models.baseline_preprocessing import BaselinePreprocessor


def _fixture() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    value = 0
    for split, day in (("train", "2018-02-14"), ("train", "2018-02-21"), ("test", "2018-02-28")):
        for index in range(4):
            rows.append(
                {
                    "f1": float(value),
                    "f2": float(value + 1),
                    "timestamp": pd.Timestamp(day) + pd.Timedelta(seconds=index * 10),
                    "capture_day": day,
                    "split": split,
                    "future_attack_state": [1, 0, 1, -1][index],
                    "future_target_available": index < 3,
                }
            )
            value += 1
    return pd.DataFrame(rows)


def test_target_is_not_shifted_twice() -> None:
    frame = _fixture()
    batch = build_sequences(frame, ["f1", "f2"], "future_attack_state", sequence_length=2, forecast_horizon=1)

    assert batch.report["target_alignment"] == "future_attack_state is read from the final input row; no second shift"
    assert batch.target_positions[0] == batch.input_end_positions[0]
    assert batch.targets[0] == 0


def test_sequences_do_not_cross_day_or_split_boundaries() -> None:
    frame = _fixture()
    batch = build_sequences(frame, ["f1", "f2"], "future_attack_state", sequence_length=2, forecast_horizon=1)

    assert set(batch.groups.tolist()) <= {"2018-02-14", "2018-02-21", "2018-02-28"}
    assert set(batch.splits.tolist()) <= {"train", "test"}
    assert all((split, group) in {("train", "2018-02-14"), ("train", "2018-02-21"), ("test", "2018-02-28")} for split, group in zip(batch.splits, batch.groups))


def test_future_and_target_columns_are_not_frozen_input_features() -> None:
    schema = yaml.safe_load(open("configs/state_feature_schema.yaml", encoding="utf-8"))
    features = set(schema["FEATURE_COLUMNS"])
    forbidden = {"future_attack_state", "binary_attack_state", "malicious_flow_count", "malicious_flow_ratio", "future_target_available", "capture_day", "timestamp"}

    assert len(features) == 17
    assert not features & forbidden


def test_preprocessing_is_fit_on_train_and_reused_without_refit() -> None:
    train = pd.DataFrame({"f1": [0.0, 2.0], "f2": [10.0, 12.0]})
    validation = pd.DataFrame({"f1": [100.0], "f2": [200.0]})
    test = pd.DataFrame({"f1": [-100.0], "f2": [-200.0]})
    preprocessor = BaselinePreprocessor(["f1", "f2"])
    preprocessor.fit(train)
    mean_before = preprocessor.scaler.mean_.copy()
    preprocessor.transform(validation)
    preprocessor.transform(test)

    assert preprocessor.fit_row_count == 2
    assert np.array_equal(mean_before, preprocessor.scaler.mean_)


def test_run_metadata_records_validation_only_selection() -> None:
    metadata_path = Path("results/lstm_v1_run_metadata.json")
    if not metadata_path.exists():
        return
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["threshold_selection_split"] == "validation"
    assert metadata["test_used_for_selection"] is False
