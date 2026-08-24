"""Train-only preprocessing artifact for the Logistic Regression baseline."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


class ModelPreprocessor:
    """Fit a fixed-column StandardScaler on training data only."""

    def __init__(self, feature_columns: list[str]) -> None:
        if not feature_columns:
            raise ValueError("At least one feature column is required")
        self.feature_columns = list(feature_columns)
        self.scaler = StandardScaler()
        self.fitted = False

    def _validate_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        missing = [column for column in self.feature_columns if column not in frame.columns]
        if missing:
            raise ValueError(f"Missing model feature columns: {missing}")
        values = frame[self.feature_columns]
        if not all(pd.api.types.is_numeric_dtype(values[column]) for column in values.columns):
            raise TypeError("All model features must be numeric")
        array = values.to_numpy(dtype="float64")
        if not np.isfinite(array).all():
            raise ValueError("Model preprocessing received non-finite values")
        if values.isna().any().any():
            raise ValueError("Model preprocessing received missing values")
        return values

    def fit(self, training_frame: pd.DataFrame) -> "ModelPreprocessor":
        values = self._validate_frame(training_frame)
        self.scaler.fit(values.to_numpy(dtype="float64"))
        self.fitted = True
        return self

    def transform(self, frame: pd.DataFrame) -> np.ndarray:
        if not self.fitted:
            raise RuntimeError("ModelPreprocessor must be fitted on training data first")
        values = self._validate_frame(frame)
        transformed = self.scaler.transform(values.to_numpy(dtype="float64"))
        if not np.isfinite(transformed).all():
            raise ValueError("Preprocessor produced non-finite values")
        return transformed

    def fit_transform(self, training_frame: pd.DataFrame) -> np.ndarray:
        return self.fit(training_frame).transform(training_frame)

    def save(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, destination)

    @classmethod
    def load(cls, path: str | Path) -> "ModelPreprocessor":
        loaded = joblib.load(path)
        if not isinstance(loaded, cls):
            raise TypeError(f"Unexpected preprocessing artifact type: {type(loaded)!r}")
        return loaded
