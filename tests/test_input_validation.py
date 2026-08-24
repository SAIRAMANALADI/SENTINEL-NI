"""Input rejection tests for the stable inference boundary."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.forecasting.inference import predict_network_state_sequence


ROOT = Path(__file__).resolve().parents[1]


def _sample() -> pd.DataFrame:
    return pd.read_csv(ROOT / "data" / "samples" / "inference_demo_sequence.csv")


def test_rejects_wrong_feature_count() -> None:
    frame = _sample().drop(columns=["flow_count"])
    with pytest.raises(ValueError, match="missing"):
        predict_network_state_sequence(frame)


def test_rejects_wrong_sequence_length() -> None:
    with pytest.raises(ValueError, match="exactly 10"):
        predict_network_state_sequence(_sample().head(9))


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_rejects_non_finite_features(value: float) -> None:
    frame = _sample()
    frame["flow_count"] = frame["flow_count"].astype(float)
    frame.loc[0, "flow_count"] = value
    with pytest.raises(ValueError, match="NaN or Inf"):
        predict_network_state_sequence(frame)


def test_rejects_wrong_feature_order() -> None:
    frame = _sample()
    columns = list(frame.columns)
    columns[0], columns[1] = columns[1], columns[0]
    with pytest.raises(ValueError, match="order"):
        predict_network_state_sequence(frame[columns])


def test_rejects_wrong_dtype() -> None:
    frame = _sample()
    frame["flow_count"] = frame["flow_count"].astype(str)
    with pytest.raises(TypeError, match="numeric dtype"):
        predict_network_state_sequence(frame)


def test_rejects_invalid_timestamp() -> None:
    frame = _sample()
    frame.loc[0, "timestamp"] = "not-a-timestamp"
    with pytest.raises(ValueError, match="invalid timestamps"):
        predict_network_state_sequence(frame)
