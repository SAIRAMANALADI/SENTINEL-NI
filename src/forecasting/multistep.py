"""Direct multi-output LSTM forecasting for approved future state targets."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd
import torch

from src.models.lstm_world_model import LSTMConfig, LSTMWorldModel, load_checkpoint


DEFAULT_CHECKPOINT = Path(__file__).resolve().parents[2] / "models" / "lstm_multistep_k1.pt"


class DirectMultiOutputLSTM(LSTMWorldModel):
    """Existing LSTM encoder with one direct logit per future step."""

    def __init__(self, config: LSTMConfig) -> None:
        if config.output_size < 1:
            raise ValueError("output_size must be positive for direct forecasting")
        super().__init__(config)


def _thresholds_for_checkpoint(
    checkpoint: dict[str, Any],
    output_size: int,
    threshold: float | Sequence[float] | None,
) -> list[float]:
    if threshold is None:
        metadata_thresholds = checkpoint.get("training_metadata", {}).get("selected_thresholds")
        if metadata_thresholds is not None:
            values = [float(value) for value in metadata_thresholds]
        else:
            values = [float(checkpoint.get("selected_threshold", 0.5))]
    elif isinstance(threshold, Sequence) and not isinstance(threshold, (str, bytes)):
        values = [float(value) for value in threshold]
    else:
        values = [float(threshold)]
    if len(values) == 1 and output_size > 1:
        values *= output_size
    if len(values) != output_size:
        raise ValueError("threshold must contain one value or one value per forecast step")
    if not all(0 <= value <= 1 for value in values):
        raise ValueError("threshold values must be in [0, 1]")
    return values


def forecast(
    sequence: np.ndarray,
    horizon: int = 1,
    checkpoint_path: str | Path = DEFAULT_CHECKPOINT,
    threshold: float | Sequence[float] | None = None,
    reference_timestamp: str | datetime | pd.Timestamp | None = None,
) -> list[dict[str, Any]]:
    """Forecast K future binary states from one historical input sequence.

    The checkpoint is a direct multi-output model: one LSTM pass produces K
    logits. The function returns no uncertainty estimate because none is
    calibrated by the approved V1 contract.
    """

    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon < 1:
        raise ValueError("horizon must be a positive integer")
    values = np.asarray(sequence, dtype="float32")
    if values.ndim != 2 or not np.isfinite(values).all():
        raise ValueError("sequence must be a finite (sequence_length, feature_count) array")
    model, checkpoint = load_checkpoint(checkpoint_path, device="cpu")
    if model.config.output_size != horizon:
        raise ValueError(
            f"checkpoint output_size={model.config.output_size} does not match horizon={horizon}"
        )
    expected = (model.config.sequence_length, model.config.input_size)
    if values.shape != expected:
        raise ValueError(f"sequence shape {values.shape} does not match expected {expected}")
    thresholds = _thresholds_for_checkpoint(checkpoint, horizon, threshold)
    with torch.no_grad():
        logits = model(torch.from_numpy(values).unsqueeze(0))
        probabilities = torch.sigmoid(logits).cpu().numpy().reshape(-1)
    if not np.isfinite(probabilities).all() or ((probabilities < 0) | (probabilities > 1)).any():
        raise ValueError("model produced non-finite or out-of-range probabilities")

    reference = None
    if reference_timestamp is not None:
        reference = pd.Timestamp(reference_timestamp)
        if pd.isna(reference):
            raise ValueError("reference_timestamp is invalid")
    output: list[dict[str, Any]] = []
    for index, probability in enumerate(probabilities, start=1):
        forecast_time = None
        if reference is not None:
            forecast_time = (reference + pd.Timedelta(seconds=10 * index)).isoformat()
        output.append(
            {
                "step": index,
                "forecast_timestamp": forecast_time,
                "prediction_probability": float(probability),
                "predicted_state": int(probability >= thresholds[index - 1]),
                "threshold": thresholds[index - 1],
                "target_column": "future_attack_state",
            }
        )
    return output
