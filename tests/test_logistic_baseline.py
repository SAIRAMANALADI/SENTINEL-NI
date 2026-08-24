from __future__ import annotations

import numpy as np
import pandas as pd

from src.models.baseline_preprocessing import BaselinePreprocessor
from src.models.logistic_baseline import LogisticBaseline


def _frame() -> tuple[pd.DataFrame, np.ndarray]:
    frame = pd.DataFrame(
        {
            "f1": [-2.0, -1.0, 1.0, 2.0, -1.5, 1.5],
            "f2": [0.0, 0.1, 0.9, 1.0, 0.2, 0.8],
        }
    )
    return frame, np.asarray([0, 0, 1, 1, 0, 1], dtype="int8")


def test_preprocessor_preserves_columns_and_fits_train_only() -> None:
    frame, target = _frame()
    preprocessor = BaselinePreprocessor(["f1", "f2"])
    transformed = preprocessor.fit_transform(frame.iloc[:4])

    assert list(transformed.columns) == ["f1", "f2"]
    assert preprocessor.fit_row_count == 4
    assert np.allclose(preprocessor.scaler.mean_, frame.iloc[:4][["f1", "f2"]].mean().to_numpy())
    validation = preprocessor.transform(frame.iloc[4:])
    assert validation.shape == (2, 2)
    assert np.isfinite(validation.to_numpy()).all()
    assert len(target) == len(frame)


def test_logistic_baseline_fits_and_predicts_probabilities() -> None:
    frame, target = _frame()
    preprocessor = BaselinePreprocessor(["f1", "f2"])
    train = preprocessor.fit_transform(frame)
    model = LogisticBaseline(["f1", "f2"], class_weight=None, random_state=42)
    model.fit(train, target)
    probabilities = model.predict_probability(train)

    assert probabilities.shape == (6,)
    assert np.isfinite(probabilities).all()
    assert set(model.predict(train, threshold=0.5)) <= {0, 1}


def test_preprocessor_rejects_nonfinite_values() -> None:
    frame, _ = _frame()
    frame.loc[0, "f1"] = np.inf
    try:
        BaselinePreprocessor(["f1", "f2"]).fit(frame)
    except ValueError as exc:
        assert "non-finite" in str(exc)
    else:
        raise AssertionError("Expected non-finite preprocessing failure")
