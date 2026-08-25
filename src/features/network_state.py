"""Deterministic fixed-interval network-state aggregation for flow exports."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


INTERVAL_CANDIDATES = (1, 5, 10, 30, 60)
DEFAULT_INTERVAL_SECONDS = 10
ANOMALY_COLUMN = "timestamp_capture_date_mismatch"

REQUIRED_COLUMNS = {
    "capture_date",
    "timestamp_parsed",
    "Label",
    "Dst Port",
    "Flow Duration",
    "Tot Fwd Pkts",
    "Tot Bwd Pkts",
    "TotLen Fwd Pkts",
    "TotLen Bwd Pkts",
    "Flow IAT Mean",
    "Flow IAT Std",
    "SYN Flag Cnt",
    "ACK Flag Cnt",
    "RST Flag Cnt",
    "Pkt Len Mean",
    "Pkt Len Std",
}
INFERENCE_REQUIRED_COLUMNS = REQUIRED_COLUMNS - {"Label"}

FEATURE_COLUMNS = [
    "flow_count",
    "byte_sum",
    "packet_sum",
    "mean_duration",
    "median_duration",
    "mean_iat",
    "iat_std",
    "syn_flow_ratio",
    "ack_flow_ratio",
    "rst_flow_ratio",
    "fwd_byte_share",
    "fwd_packet_share",
    "unique_destination_port_count",
    "bytes_per_second",
    "packets_per_second",
    "packet_size_mean",
    "packet_size_std",
]
TARGET_COLUMNS = [
    "malicious_flow_count",
    "malicious_flow_ratio",
    "binary_attack_state",
    "future_attack_state",
    "future_target_available",
]
METADATA_COLUMNS = ["timestamp", "capture_day"]


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    values = pd.to_numeric(frame[column], errors="coerce")
    if values.isna().any() or not np.isfinite(values.to_numpy(dtype="float64")).all():
        raise ValueError(f"Required state source column is missing/non-finite: {column}")
    return values.astype("float64")


def _validate_input(frame: pd.DataFrame, *, require_label: bool = True) -> pd.DataFrame:
    required_columns = REQUIRED_COLUMNS if require_label else INFERENCE_REQUIRED_COLUMNS
    missing = sorted(required_columns.difference(frame.columns))
    if missing:
        raise ValueError(f"Missing network-state source columns: {missing}")
    result = frame.copy()
    result["timestamp_parsed"] = pd.to_datetime(result["timestamp_parsed"], errors="coerce")
    if result["timestamp_parsed"].isna().any():
        raise ValueError("Network-state input contains invalid timestamps")
    result["capture_date"] = result["capture_date"].astype("string")
    if result["capture_date"].isna().any():
        raise ValueError("Network-state input contains missing capture dates")
    if ANOMALY_COLUMN not in result.columns:
        result[ANOMALY_COLUMN] = False
    result[ANOMALY_COLUMN] = result[ANOMALY_COLUMN].astype(bool)
    result = result.loc[~result[ANOMALY_COLUMN]].copy()
    expected_dates = result["timestamp_parsed"].dt.strftime("%Y-%m-%d")
    mismatch = expected_dates.ne(result["capture_date"])
    if mismatch.any():
        raise ValueError("Timestamp/capture-date anomalies must be excluded before aggregation")
    return result


def _add_derived_flow_columns(frame: pd.DataFrame, *, require_label: bool = True) -> pd.DataFrame:
    result = frame.copy()
    fwd_bytes = _numeric(result, "TotLen Fwd Pkts")
    bwd_bytes = _numeric(result, "TotLen Bwd Pkts")
    fwd_packets = _numeric(result, "Tot Fwd Pkts")
    bwd_packets = _numeric(result, "Tot Bwd Pkts")
    result["_byte_sum"] = fwd_bytes + bwd_bytes
    result["_packet_sum"] = fwd_packets + bwd_packets
    result["_fwd_bytes"] = fwd_bytes
    result["_bwd_bytes"] = bwd_bytes
    result["_fwd_packets"] = fwd_packets
    result["_bwd_packets"] = bwd_packets
    result["_duration"] = _numeric(result, "Flow Duration")
    result["_flow_iat_mean"] = _numeric(result, "Flow IAT Mean")
    result["_flow_iat_std"] = _numeric(result, "Flow IAT Std")
    result["_syn_flow"] = _numeric(result, "SYN Flag Cnt").gt(0).astype("float64")
    result["_ack_flow"] = _numeric(result, "ACK Flag Cnt").gt(0).astype("float64")
    result["_rst_flow"] = _numeric(result, "RST Flag Cnt").gt(0).astype("float64")
    result["_packet_size_mean"] = _numeric(result, "Pkt Len Mean")
    result["_packet_size_std"] = _numeric(result, "Pkt Len Std")
    if require_label:
        result["_malicious"] = result["Label"].astype("string").ne("Benign").astype("int64")
    return result


def _complete_state_index(frame: pd.DataFrame, interval_seconds: int) -> pd.DataFrame:
    parts = []
    frequency = f"{interval_seconds}s"
    for capture_day, day_frame in frame.groupby("capture_date", sort=True):
        start = day_frame["timestamp_parsed"].min().floor(frequency)
        end = day_frame["timestamp_parsed"].max().floor(frequency)
        timestamps = pd.date_range(start, end, freq=frequency)
        parts.append(
            pd.DataFrame(
                {
                    "capture_day": str(capture_day),
                    "timestamp": timestamps,
                }
            )
        )
    if not parts:
        raise ValueError("No valid flows remain after anomaly exclusion")
    return pd.concat(parts, ignore_index=True)


def aggregate_network_states(
    frame: pd.DataFrame,
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
    *,
    mode: str = "supervised",
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Aggregate fixed intervals independently within each capture day.

    ``mode="supervised"`` preserves the frozen training/evaluation contract,
    including labels and target columns. ``mode="inference"`` uses the same
    feature arithmetic but requires no label and emits only model inputs plus
    timestamp/capture-day metadata.
    """
    if interval_seconds not in INTERVAL_CANDIDATES:
        raise ValueError(f"interval_seconds must be one of {INTERVAL_CANDIDATES}")
    if mode not in {"supervised", "inference"}:
        raise ValueError("mode must be 'supervised' or 'inference'")
    supervised = mode == "supervised"
    clean = _add_derived_flow_columns(
        _validate_input(frame, require_label=supervised),
        require_label=supervised,
    )
    clean["_state_timestamp"] = clean["timestamp_parsed"].dt.floor(f"{interval_seconds}s")
    grouped = clean.groupby(["capture_date", "_state_timestamp"], sort=True, observed=True)
    aggregation_spec: dict[str, tuple[str, str]] = {
        "flow_count": ("_byte_sum", "size"),
        "byte_sum": ("_byte_sum", "sum"),
        "packet_sum": ("_packet_sum", "sum"),
        "fwd_byte_sum": ("_fwd_bytes", "sum"),
        "bwd_byte_sum": ("_bwd_bytes", "sum"),
        "fwd_packet_sum": ("_fwd_packets", "sum"),
        "bwd_packet_sum": ("_bwd_packets", "sum"),
        "mean_duration": ("_duration", "mean"),
        "median_duration": ("_duration", "median"),
        "mean_iat": ("_flow_iat_mean", "mean"),
        "iat_std": ("_flow_iat_std", "mean"),
        "syn_flow_sum": ("_syn_flow", "sum"),
        "ack_flow_sum": ("_ack_flow", "sum"),
        "rst_flow_sum": ("_rst_flow", "sum"),
        "unique_destination_port_count": ("Dst Port", "nunique"),
        "packet_size_mean": ("_packet_size_mean", "mean"),
        "packet_size_std": ("_packet_size_std", "mean"),
    }
    if supervised:
        aggregation_spec["malicious_flow_count"] = ("_malicious", "sum")
    aggregated = grouped.agg(**aggregation_spec).reset_index()
    aggregated = aggregated.rename(columns={"capture_date": "capture_day", "_state_timestamp": "timestamp"})
    states = _complete_state_index(clean, interval_seconds).merge(
        aggregated,
        on=["capture_day", "timestamp"],
        how="left",
        sort=False,
    )
    count_columns = [
        "flow_count",
        "byte_sum",
        "packet_sum",
        "fwd_byte_sum",
        "bwd_byte_sum",
        "fwd_packet_sum",
        "bwd_packet_sum",
        "syn_flow_sum",
        "ack_flow_sum",
        "rst_flow_sum",
        "unique_destination_port_count",
    ]
    if supervised:
        count_columns.append("malicious_flow_count")
    states[count_columns] = states[count_columns].fillna(0)
    states["flow_count"] = states["flow_count"].astype("int64")
    if supervised:
        states["malicious_flow_count"] = states["malicious_flow_count"].astype("int64")
    states["unique_destination_port_count"] = states["unique_destination_port_count"].astype("int64")
    for column in [
        "byte_sum",
        "packet_sum",
        "fwd_byte_sum",
        "bwd_byte_sum",
        "fwd_packet_sum",
        "bwd_packet_sum",
        "mean_duration",
        "median_duration",
        "mean_iat",
        "iat_std",
        "syn_flow_sum",
        "ack_flow_sum",
        "rst_flow_sum",
        "packet_size_mean",
        "packet_size_std",
    ]:
        states[column] = states[column].fillna(0.0).astype("float64")
    denominator = states["flow_count"].replace(0, np.nan)
    states["syn_flow_ratio"] = (states["syn_flow_sum"] / denominator).fillna(0.0)
    states["ack_flow_ratio"] = (states["ack_flow_sum"] / denominator).fillna(0.0)
    states["rst_flow_ratio"] = (states["rst_flow_sum"] / denominator).fillna(0.0)
    byte_denominator = states["byte_sum"].replace(0, np.nan)
    packet_denominator = states["packet_sum"].replace(0, np.nan)
    states["fwd_byte_share"] = (states["fwd_byte_sum"] / byte_denominator).fillna(0.0)
    states["fwd_packet_share"] = (states["fwd_packet_sum"] / packet_denominator).fillna(0.0)
    states["bytes_per_second"] = states["byte_sum"] / float(interval_seconds)
    states["packets_per_second"] = states["packet_sum"] / float(interval_seconds)
    if supervised:
        states["malicious_flow_ratio"] = (states["malicious_flow_count"] / denominator).fillna(0.0)
        states["binary_attack_state"] = states["malicious_flow_count"].gt(0).astype("int8")
        states["future_attack_state"] = (
            states.groupby("capture_day", sort=False)["binary_attack_state"].shift(-1)
        )
        states["future_target_available"] = states["future_attack_state"].notna()
        states["future_attack_state"] = states["future_attack_state"].fillna(-1).astype("int8")
    states = states.sort_values(["capture_day", "timestamp"], kind="mergesort").reset_index(drop=True)
    output_columns = (
        METADATA_COLUMNS + FEATURE_COLUMNS + TARGET_COLUMNS
        if supervised
        else FEATURE_COLUMNS + METADATA_COLUMNS
    )
    states = states[output_columns]
    feature_values = states[FEATURE_COLUMNS].to_numpy(dtype="float64")
    if states[FEATURE_COLUMNS].isna().any().any() or not np.isfinite(feature_values).all():
        raise ValueError("Network-state features contain missing or non-finite values")
    report = {
        "interval_seconds": interval_seconds,
        "total_states": int(len(states)),
        "nonempty_states": int((states["flow_count"] > 0).sum()),
        "empty_states": int((states["flow_count"] == 0).sum()),
        "empty_state_percentage": float((states["flow_count"] == 0).mean() * 100),
        "total_valid_input_flows": int(len(clean)),
        "excluded_timestamp_anomalies": int(len(frame) - len(clean)),
        "mean_flows_per_state": float(states["flow_count"].mean()),
        "median_flows_per_state": float(states["flow_count"].median()),
        "p95_flows_per_state": float(states["flow_count"].quantile(0.95)),
        "mean_flows_per_nonempty_state": float(states.loc[states["flow_count"] > 0, "flow_count"].mean()),
        "feature_count": len(FEATURE_COLUMNS),
        "feature_columns": FEATURE_COLUMNS,
        "target_columns": TARGET_COLUMNS if supervised else [],
        "mode": mode,
        "model_input_has_nan_or_inf": False,
    }
    if supervised:
        report["infiltration_state_frequency_all_states"] = float(states["binary_attack_state"].mean())
        report["infiltration_state_frequency_nonempty_states"] = float(
            states.loc[states["flow_count"] > 0, "binary_attack_state"].mean()
        )
    return states, report


def build_network_state_for_inference(
    frame: pd.DataFrame,
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Build the exact model-input state without labels or future targets."""

    return aggregate_network_states(frame, interval_seconds=interval_seconds, mode="inference")
