"""Logistic Regression current-state baseline."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression


class LogisticBaseline:
    """Reproducible binary Logistic Regression model for P(attack_t)."""

    def __init__(
        self,
        feature_columns: list[str],
        C: float = 1.0,
        class_weight: str | dict[int, float] | None = "balanced",
        random_state: int = 42,
        max_iter: int = 1000,
    ) -> None:
        self.feature_columns = list(feature_columns)
        self.class_weight = class_weight
        self.model = LogisticRegression(
            C=C,
            class_weight=class_weight,
            max_iter=max_iter,
            random_state=random_state,
            solver="liblinear",
        )

    def fit(self, features: pd.DataFrame | np.ndarray, target: np.ndarray) -> "LogisticBaseline":
        values = features[self.feature_columns] if isinstance(features, pd.DataFrame) else features
        self.model.fit(values, np.asarray(target, dtype="int8"))
        return self

    def predict_probability(self, features: pd.DataFrame | np.ndarray) -> np.ndarray:
        values = features[self.feature_columns] if isinstance(features, pd.DataFrame) else features
        probability = self.model.predict_proba(values)[:, 1]
        if not np.isfinite(probability).all():
            raise ValueError("Logistic Regression produced non-finite probabilities")
        return probability

    def predict(self, features: pd.DataFrame | np.ndarray) -> np.ndarray:
        values = features[self.feature_columns] if isinstance(features, pd.DataFrame) else features
        return self.model.predict(values)

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
