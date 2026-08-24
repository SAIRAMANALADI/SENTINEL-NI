"""Source-risk records that preserve uncertainty and avoid attribution claims."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from src.streaming.source_activity import SOURCE_ACTIVITY_COLUMNS


def build_source_risk_table(
    activity: pd.DataFrame,
    forecast_context: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return candidate-source records without producing source probabilities."""

    missing = [column for column in SOURCE_ACTIVITY_COLUMNS if column not in activity.columns]
    if missing:
        raise ValueError(f"source activity is missing required columns: {missing}")
    context = dict(forecast_context or {})
    rows: list[dict[str, Any]] = []
    for row in activity.to_dict(orient="records"):
        features = {column: row[column] for column in SOURCE_ACTIVITY_COLUMNS if column not in {"source_ip", "capture_day", "interval_start", "interval_end"}}
        rows.append(
            {
                "source_ip": str(row["source_ip"]),
                "interval_start": pd.Timestamp(row["interval_start"]).isoformat(),
                "interval_end": pd.Timestamp(row["interval_end"]).isoformat(),
                "activity_features": features,
                "forecast_context": context.copy(),
                "risk_status": "candidate source",
            }
        )
    return rows
