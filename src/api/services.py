"""Thin service adapters that compose the existing scientific modules."""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from src.evaluation.mitigation_policy import recommendations_for_sources
from src.forecasting.inference import predict_network_state_sequence
from src.streaming.source_activity import aggregate_source_activity
from src.streaming.source_forecast import prioritize_sources


FEATURE_CONTEXT_COLUMNS = ("timestamp", "capture_day")


def forecast_payload(sequence: list[Any], top_n: int, settings: Any) -> dict[str, Any]:
    feature_columns = _feature_columns(settings.feature_schema_path)
    records: list[dict[str, Any]] = []
    for point in sequence:
        features = dict(point.features)
        if set(features) != set(feature_columns):
            missing = sorted(set(feature_columns) - set(features))
            unexpected = sorted(set(features) - set(feature_columns))
            raise ValueError(f"feature contract mismatch; missing={missing}, unexpected={unexpected}")
        records.append({**features, "timestamp": point.timestamp, "capture_day": point.capture_day.isoformat()})
    frame = pd.DataFrame(records, columns=[*feature_columns, *FEATURE_CONTEXT_COLUMNS])
    result = dict(
        predict_network_state_sequence(
            frame,
            checkpoint_path=settings.model_path,
            policy_path=settings.operating_policy_path,
            schema_path=settings.feature_schema_path,
            top_n=top_n,
        )
    )
    result.pop("model_checkpoint", None)
    result["service_state"] = "HEALTHY"
    return result


def source_priority_payload(request: Any) -> dict[str, Any]:
    events = []
    for event in request.events:
        row = event.model_dump()
        row["source_ip"] = str(row["source_ip"])
        row["destination_ip"] = str(row["destination_ip"])
        events.append(row)
    activity = aggregate_source_activity(events)
    context = {
        "forecast": [
            {
                "score": request.forecast_score,
                "warning": request.network_warning,
            }
        ]
        if request.forecast_score is not None or request.network_warning is not None
        else [],
        "reference_timestamp": request.reference_timestamp.isoformat() if request.reference_timestamp else None,
    }
    prioritized = prioritize_sources(activity, context)
    return {
        "service_state": "HEALTHY",
        "source_count": int(len(prioritized)),
        "source_priorities": _json_records(prioritized.to_dict(orient="records")),
    }


def mitigation_payload(request: Any) -> dict[str, Any]:
    rows = []
    for source in request.sources:
        rows.append(
            {
                "source_ip": str(source.source_ip),
                "priority": source.priority,
                "priority_points": source.priority_points,
            }
        )
    recommendations = recommendations_for_sources(rows)
    for recommendation in recommendations:
        recommendation["simulation_only"] = True
    return {"service_state": "HEALTHY", "simulation_only": True, "recommendations": recommendations}


def _feature_columns(path: Any) -> list[str]:
    import yaml

    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    columns = document.get("FEATURE_COLUMNS") if isinstance(document, dict) else None
    if not isinstance(columns, list) or len(columns) != 17:
        raise ValueError("feature schema must define exactly 17 features")
    return [str(column) for column in columns]


def _json_records(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in rows:
        item: dict[str, Any] = {}
        for key, value in row.items():
            if isinstance(value, (pd.Timestamp, datetime)):
                item[key] = value.isoformat()
            elif hasattr(value, "item"):
                item[key] = value.item()
            else:
                item[key] = value
        normalized.append(item)
    return normalized

