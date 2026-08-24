"""Load the separately stored target/timestamp sidecar for model features."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


SIDECAR_COLUMNS = [
    "timestamp_parsed",
    "binary_label",
    "original_label",
    "Label",
    "source_row_number",
    "Timestamp",
    "Dst Port",
    "Protocol",
    "Flow Byts/s",
    "Flow Pkts/s",
]
DUPLICATE_KEY_COLUMNS = ["Timestamp", "Dst Port", "Protocol", "Flow Byts/s", "Flow Pkts/s", "Label"]


def companion_clean_path(model_features_path: str | Path) -> Path:
    source = Path(model_features_path).expanduser().resolve()
    if source.name.endswith("_model_features.parquet"):
        return source.with_name(source.name.replace("_model_features.parquet", "_flow_clean.parquet"))
    return source.with_name("cic_ids2018_flow_clean.parquet")


def load_modeling_frame(model_features_path: str | Path) -> tuple[pd.DataFrame, list[str], Path]:
    """Join model-safe numeric features to the clean target/time sidecar by row order."""
    feature_path = Path(model_features_path).expanduser().resolve()
    clean_path = companion_clean_path(feature_path)
    if not feature_path.is_file():
        raise FileNotFoundError(f"Model feature dataset does not exist: {feature_path}")
    if not clean_path.is_file():
        raise FileNotFoundError(f"Clean sidecar dataset does not exist: {clean_path}")

    features = pd.read_parquet(feature_path)
    # Read the known sidecar columns directly; the actual clean artifact is validated by row count.
    sidecar = pd.read_parquet(clean_path, columns=SIDECAR_COLUMNS)
    if len(features) != len(sidecar):
        raise ValueError(
            f"Feature/sidecar row counts differ: features={len(features)}, sidecar={len(sidecar)}"
        )
    if not features.index.equals(sidecar.index):
        sidecar = sidecar.reset_index(drop=True)
        features = features.reset_index(drop=True)
    feature_columns = list(features.columns)
    if not feature_columns or not all(pd.api.types.is_numeric_dtype(features[column]) for column in feature_columns):
        raise TypeError("Model feature dataset must contain only numeric feature columns")
    return pd.concat([features.reset_index(drop=True), sidecar.reset_index(drop=True)], axis=1), feature_columns, clean_path
