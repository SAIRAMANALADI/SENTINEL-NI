from __future__ import annotations

import numpy as np
import pandas as pd
import yaml

from src.models.baseline_preprocessing import BaselinePreprocessor


def test_frozen_schema_excludes_target_and_future_fields() -> None:
    schema = yaml.safe_load(open("configs/state_feature_schema.yaml", encoding="utf-8"))
    features = set(schema["FEATURE_COLUMNS"])
    targets = set(schema["TARGET_COLUMNS"])
    forbidden = {"future_attack_state", "binary_attack_state", "malicious_flow_count", "malicious_flow_ratio", "future_target_available"}

    assert len(features) == 17
    assert not features & targets
    assert not features & forbidden
    assert "capture_day" not in features
    assert "timestamp" not in features


def test_validation_and_test_use_train_fitted_transformation() -> None:
    train = pd.DataFrame({"f1": [0.0, 2.0], "f2": [10.0, 12.0]})
    validation = pd.DataFrame({"f1": [100.0], "f2": [200.0]})
    test = pd.DataFrame({"f1": [-100.0], "f2": [-200.0]})
    preprocessor = BaselinePreprocessor(["f1", "f2"])
    preprocessor.fit(train)
    train_mean_before = preprocessor.scaler.mean_.copy()
    preprocessor.transform(validation)
    preprocessor.transform(test)

    assert preprocessor.fit_row_count == 2
    assert np.array_equal(preprocessor.scaler.mean_, train_mean_before)
    assert np.array_equal(preprocessor.get_feature_names_out(), np.asarray(["f1", "f2"], dtype=object))


def test_training_script_selects_threshold_on_validation_only() -> None:
    source = open("scripts/train_baseline.py", encoding="utf-8").read()

    assert 'threshold_table(targets["validation"]' in source
    assert 'threshold_table(targets["test"]' not in source
    assert 'test_metrics = evaluate_binary(targets["test"]' in source
