"""Configurable LSTM world-model baseline for frozen V1 state sequences."""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn


@dataclass(frozen=True)
class LSTMConfig:
    input_size: int = 17
    hidden_size: int = 64
    num_layers: int = 1
    dropout: float = 0.0
    learning_rate: float = 1e-3
    batch_size: int = 128
    epochs: int = 20
    sequence_length: int = 10
    forecast_horizon: int = 1
    random_seed: int = 42
    device: str = "cpu"
    output_size: int = 1

    def __post_init__(self) -> None:
        if self.input_size < 1 or self.hidden_size < 1 or self.num_layers < 1 or self.output_size < 1:
            raise ValueError("input_size, hidden_size, num_layers, and output_size must be positive")
        if not 0 <= self.dropout < 1:
            raise ValueError("dropout must be in [0, 1)")
        if self.learning_rate <= 0 or self.batch_size < 1 or self.epochs < 1:
            raise ValueError("learning_rate, batch_size, and epochs must be positive")
        if self.sequence_length < 1 or self.forecast_horizon < 1:
            raise ValueError("sequence_length and forecast_horizon must be positive")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class LSTMWorldModel(nn.Module):
    """LSTM sequence encoder with a single binary logit output."""

    def __init__(self, config: LSTMConfig) -> None:
        super().__init__()
        self.config = config
        lstm_dropout = config.dropout if config.num_layers > 1 else 0.0
        self.encoder = nn.LSTM(
            input_size=config.input_size,
            hidden_size=config.hidden_size,
            num_layers=config.num_layers,
            dropout=lstm_dropout,
            batch_first=True,
        )
        self.output_head = nn.Linear(config.hidden_size, config.output_size)

    def forward(self, sequences: torch.Tensor) -> torch.Tensor:
        if sequences.ndim != 3:
            raise ValueError("Expected input shape (batch, sequence_length, input_size)")
        if sequences.shape[1] != self.config.sequence_length:
            raise ValueError("Input sequence length does not match model configuration")
        if sequences.shape[2] != self.config.input_size:
            raise ValueError("Input feature dimension does not match model configuration")
        outputs, _ = self.encoder(sequences)
        final_hidden = outputs[:, -1, :]
        logits = self.output_head(final_hidden)
        return logits.squeeze(-1) if self.config.output_size == 1 else logits


def set_deterministic_seed(seed: int) -> None:
    """Set deterministic Python, NumPy, and PyTorch CPU seeds."""

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)


def save_checkpoint(
    path: str | Path,
    model: LSTMWorldModel,
    feature_columns: list[str],
    target_column: str,
    target_version: str,
    feature_schema_version: str,
    selected_threshold: float,
    best_epoch: int,
    best_validation_metric: float,
    training_metadata: dict[str, Any],
) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "state_dict": model.state_dict(),
            "config": model.config.to_dict(),
            "feature_columns": list(feature_columns),
            "target_column": target_column,
            "target_version": target_version,
            "feature_schema_version": feature_schema_version,
            "selected_threshold": float(selected_threshold),
            "best_epoch": int(best_epoch),
            "best_validation_metric": float(best_validation_metric),
            "training_metadata": training_metadata,
        },
        destination,
    )


def load_checkpoint(path: str | Path, device: str = "cpu") -> tuple[LSTMWorldModel, dict[str, Any]]:
    checkpoint = torch.load(Path(path), map_location=device, weights_only=False)
    config = LSTMConfig(**checkpoint["config"])
    model = LSTMWorldModel(config)
    model.load_state_dict(checkpoint["state_dict"])
    model.to(device)
    model.eval()
    return model, checkpoint
