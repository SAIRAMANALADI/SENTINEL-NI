"""Logistic Regression baseline for the frozen V1 network-state contract."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression


class LogisticBaseline:
    """Deterministic binary Logistic Regression wrapper with fixed feature names."""

    def __init__(
        self,
        feature_columns: list[str],
        C: float = 1.0,
        max_iter: int = 1000,
        class_weight: str | dict[int, float] | None = None,
        random_state: int = 42,
    ) -> None:
        if not feature_columns:
            raise ValueError("feature_columns must not be empty")
        if C <= 0:
            raise ValueError("C must be positive")
        if max_iter < 1:
            raise ValueError("max_iter must be positive")
        self.feature_columns = list(feature_columns)
        self.C = float(C)
        self.max_iter = int(max_iter)
        self.class_weight = class_weight
        self.random_state = int(random_state)
        self.model = LogisticRegression(
            C=self.C,
            max_iter=self.max_iter,
            class_weight=self.class_weight,
            random_state=self.random_state,
            solver="liblinear",
        )

    def _values(self, features: pd.DataFrame | np.ndarray) -> np.ndarray:
        if isinstance(features, pd.DataFrame):
            missing = [column for column in self.feature_columns if column not in features.columns]
            if missing:
                raise ValueError(f"Missing model feature columns: {missing}")
            values = features[self.feature_columns].to_numpy(dtype="float64")
        else:
            values = np.asarray(features, dtype="float64")
        if values.ndim != 2 or values.shape[1] != len(self.feature_columns):
            raise ValueError("Feature matrix has an unexpected shape")
        if not np.isfinite(values).all():
            raise ValueError("Logistic Regression received non-finite features")
        return values

    def fit(self, features: pd.DataFrame | np.ndarray, target: np.ndarray) -> "LogisticBaseline":
        values = self._values(features)
        labels = np.asarray(target, dtype="int8")
        if len(labels) != len(values):
            raise ValueError("Feature and target row counts differ")
        if set(np.unique(labels)) - {0, 1}:
            raise ValueError("Logistic baseline target must contain only 0 and 1")
        self.model.fit(values, labels)
        return self

    def predict_probability(self, features: pd.DataFrame | np.ndarray) -> np.ndarray:
        probability = self.model.predict_proba(self._values(features))[:, 1]
        if not np.isfinite(probability).all():
            raise ValueError("Logistic Regression produced non-finite probabilities")
        return probability

    def predict(self, features: pd.DataFrame | np.ndarray, threshold: float = 0.5) -> np.ndarray:
        if not 0 <= threshold <= 1:
            raise ValueError("threshold must be between 0 and 1")
        return (self.predict_probability(features) >= threshold).astype("int8")

    def save(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, destination)

    @classmethod
    def load(cls, path: str | Path) -> "LogisticBaseline":
        loaded = joblib.load(path)
        if not isinstance(loaded, cls):
            raise TypeError(f"Unexpected baseline artifact type: {type(loaded)!r}")
        return loaded
