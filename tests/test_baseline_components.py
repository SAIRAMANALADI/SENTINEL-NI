from __future__ import annotations

import numpy as np
import pandas as pd

from src.evaluation.metrics import evaluate_binary
from src.preprocessing.model_preprocess import ModelPreprocessor


def test_preprocessor_fits_on_train_and_preserves_feature_order() -> None:
    train = pd.DataFrame({"b": [10.0, 20.0], "a": [1.0, 3.0]})
    validation = pd.DataFrame({"a": [5.0], "b": [30.0]})
    preprocessor = ModelPreprocessor(["b", "a"])
    transformed = preprocessor.fit_transform(train)
    validation_transformed = preprocessor.transform(validation)

    assert transformed.shape == (2, 2)
    assert validation_transformed.shape == (1, 2)
    assert np.allclose(preprocessor.scaler.mean_, [15.0, 2.0])
    assert np.isfinite(validation_transformed).all()


def test_metrics_include_required_fields() -> None:
    metrics = evaluate_binary(
        np.array([0, 0, 1, 1]),
        np.array([0.1, 0.4, 0.6, 0.9]),
    )

    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1"] == 1.0
    assert metrics["false_positive_rate"] == 0.0
    assert metrics["roc_auc"] == 1.0
    assert metrics["pr_auc"] == 1.0
    assert metrics["confusion_matrix"] == [[2, 0], [0, 2]]
