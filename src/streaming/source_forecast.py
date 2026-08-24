"""Transparent source prioritization beside the frozen network forecast."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd

from src.evaluation.source_risk import build_source_risk_table
from src.streaming.source_activity import SOURCE_ACTIVITY_COLUMNS


def extract_forecast_context(network_forecast: Mapping[str, Any] | None) -> dict[str, Any]:
    """Extract non-attributive network context from the existing forecast result."""

    if not network_forecast:
        return {"available": False, "forecast_score": None, "network_warning": None}
    rows = network_forecast.get("forecast") or []
    first = rows[0] if rows else {}
    score = first.get("score")
    if score is not None:
        score = float(score)
        if not np.isfinite(score):
            raise ValueError("network forecast score must be finite")
    return {
        "available": bool(rows),
        "forecast_score": score,
        "network_warning": bool(first.get("warning")) if rows else None,
        "reference_timestamp": network_forecast.get("reference_timestamp") or network_forecast.get("current_timestamp"),
    }


def prioritize_sources(
    activity: pd.DataFrame,
    network_forecast: Mapping[str, Any] | None = None,
) -> pd.DataFrame:
    """Assign transparent HIGH/MEDIUM/LOW priority labels with measured reasons."""

    missing = [column for column in SOURCE_ACTIVITY_COLUMNS if column not in activity.columns]
    if missing:
        raise ValueError(f"source activity is missing required columns: {missing}")
    if activity.empty:
        return pd.DataFrame(
            columns=[
                *SOURCE_ACTIVITY_COLUMNS,
                "flow_growth",
                "packet_growth",
                "byte_growth",
                "priority_points",
                "priority",
                "measured_reasons",
                "risk_status",
                "forecast_context",
            ]
        )

    context = extract_forecast_context(network_forecast)
    result = activity.copy().sort_values(["source_ip", "interval_start"], kind="mergesort").reset_index(drop=True)
    result["_previous_flow_count"] = result.groupby("source_ip", sort=False)["flow_count"].shift(1)
    result["_previous_packet_count"] = result.groupby("source_ip", sort=False)["packet_count"].shift(1)
    result["_previous_byte_count"] = result.groupby("source_ip", sort=False)["byte_count"].shift(1)
    result["flow_growth"] = ((result["flow_count"] - result["_previous_flow_count"]) / result["_previous_flow_count"].clip(lower=1)).fillna(0.0)
    result["packet_growth"] = ((result["packet_count"] - result["_previous_packet_count"]) / result["_previous_packet_count"].clip(lower=1)).fillna(0.0)
    result["byte_growth"] = ((result["byte_count"] - result["_previous_byte_count"]) / result["_previous_byte_count"].clip(lower=1)).fillna(0.0)

    priorities: list[dict[str, Any]] = []
    for row in result.to_dict(orient="records"):
        points = 0
        reasons: list[str] = []
        if row["flow_growth"] >= 0.5:
            points += 2
            reasons.append(f"flow_count growth {row['flow_growth']:.0%}")
        elif row["flow_growth"] > 0:
            points += 1
            reasons.append(f"flow_count growth {row['flow_growth']:.0%}")
        if row["packet_rate"] >= 3.0 or row["byte_rate"] >= 5000.0:
            points += 2
            reasons.append(f"packet_rate={row['packet_rate']:.2f}/s, byte_rate={row['byte_rate']:.2f}/s")
        elif row["packet_rate"] >= 1.0 or row["byte_rate"] >= 1000.0:
            points += 1
            reasons.append(f"packet_rate={row['packet_rate']:.2f}/s, byte_rate={row['byte_rate']:.2f}/s")
        if row["unique_destinations"] >= 3:
            points += 1
            reasons.append(f"destinations={int(row['unique_destinations'])}")
        if row["unique_destination_ports"] >= 3:
            points += 1
            reasons.append(f"destination_ports={int(row['unique_destination_ports'])}")
        if context["network_warning"]:
            points += 1
            reasons.append("network forecast is elevated")
        if points >= 5:
            priority = "HIGH PRIORITY SOURCE"
        elif points >= 3:
            priority = "MEDIUM PRIORITY SOURCE"
        else:
            priority = "LOW PRIORITY SOURCE"
        priorities.append(
            {
                **{column: row[column] for column in SOURCE_ACTIVITY_COLUMNS},
                "flow_growth": float(row["flow_growth"]),
                "packet_growth": float(row["packet_growth"]),
                "byte_growth": float(row["byte_growth"]),
                "priority_points": points,
                "priority": priority,
                "measured_reasons": "; ".join(reasons) if reasons else "no threshold crossed",
                "risk_status": "candidate source",
                "forecast_context": context.copy(),
            }
        )
    return pd.DataFrame(priorities)


def prioritize_sources_with_forecast(activity: pd.DataFrame, network_forecast: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return JSON-friendly source records paired with network forecast context."""

    prioritized = prioritize_sources(activity, network_forecast)
    risk_rows = build_source_risk_table(activity, extract_forecast_context(network_forecast))
    risk_by_key = {(row["source_ip"], row["interval_start"]): row for row in risk_rows}
    output: list[dict[str, Any]] = []
    for row in prioritized.to_dict(orient="records"):
        key = (str(row["source_ip"]), pd.Timestamp(row["interval_start"]).isoformat())
        risk = risk_by_key.get(key, {})
        row["activity_features"] = risk.get("activity_features", {})
        row["interval_start"] = pd.Timestamp(row["interval_start"]).isoformat()
        row["interval_end"] = pd.Timestamp(row["interval_end"]).isoformat()
        output.append(row)
    return output
