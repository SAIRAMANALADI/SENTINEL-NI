"""Train-only preprocessing for the frozen V1 Logistic Regression baseline."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


class BaselinePreprocessor:
    """Fixed-column StandardScaler fitted exclusively on the training frame."""

    def __init__(self, feature_columns: list[str]) -> None:
        if not feature_columns:
            raise ValueError("feature_columns must not be empty")
        if len(set(feature_columns)) != len(feature_columns):
            raise ValueError("feature_columns must be unique")
        self.feature_columns = list(feature_columns)
        self.scaler = StandardScaler()
        self.fitted = False
        self.fit_row_count: int | None = None

    def _validate_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        if not isinstance(frame, pd.DataFrame):
            raise TypeError("frame must be a pandas DataFrame")
        missing = [column for column in self.feature_columns if column not in frame.columns]
        if missing:
            raise ValueError(f"Missing model feature columns: {missing}")
        values = frame[self.feature_columns]
        if not all(pd.api.types.is_numeric_dtype(values[column]) for column in values.columns):
            raise TypeError("All baseline features must be numeric")
        if values.isna().any().any():
            raise ValueError("Baseline preprocessing received NaN values")
        array = values.to_numpy(dtype="float64")
        if not np.isfinite(array).all():
            raise ValueError("Baseline preprocessing received non-finite values")
        return values

    def fit(self, training_frame: pd.DataFrame) -> "BaselinePreprocessor":
        values = self._validate_frame(training_frame)
        if values.empty:
            raise ValueError("Cannot fit preprocessing on an empty training frame")
        self.scaler.fit(values.to_numpy(dtype="float64"))
        self.fitted = True
        self.fit_row_count = int(len(values))
        return self

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        if not self.fitted:
            raise RuntimeError("BaselinePreprocessor must be fitted on training data first")
        values = self._validate_frame(frame)
        transformed = self.scaler.transform(values.to_numpy(dtype="float64"))
        if not np.isfinite(transformed).all():
            raise ValueError("Baseline preprocessing produced non-finite values")
        return pd.DataFrame(transformed, columns=self.feature_columns, index=frame.index)

    def fit_transform(self, training_frame: pd.DataFrame) -> pd.DataFrame:
        return self.fit(training_frame).transform(training_frame)

    def get_feature_names_out(self) -> np.ndarray:
        return np.asarray(self.feature_columns, dtype=object)

    def save(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, destination)

    @classmethod
    def load(cls, path: str | Path) -> "BaselinePreprocessor":
        loaded = joblib.load(path)
        if not isinstance(loaded, cls):
            raise TypeError(f"Unexpected preprocessing artifact type: {type(loaded)!r}")
        return loaded
