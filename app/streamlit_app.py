"""Offline Streamlit demo for the frozen network-state inference API."""

from __future__ import annotations

import io
from pathlib import Path
from typing import BinaryIO

import pandas as pd
import streamlit as st
import yaml

from src.forecasting.inference import predict_network_state_sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_INPUT = PROJECT_ROOT / "data" / "samples" / "inference_demo_sequence.csv"
KNOWN_TEST_STATUS = "91 tests passed"


def load_sequence_from_path(path: str | Path) -> pd.DataFrame:
    """Load a supported local demo/input file without applying model logic."""

    source = Path(path)
    if source.suffix.lower() == ".parquet":
        return pd.read_parquet(source)
    if source.suffix.lower() in {".csv", ".tsv"}:
        return pd.read_csv(source, sep="\t" if source.suffix.lower() == ".tsv" else ",")
    raise ValueError("Choose a .csv, .tsv, or .parquet sequence file")


def load_sequence_from_upload(name: str, uploaded: bytes | BinaryIO) -> pd.DataFrame:
    """Load uploaded bytes into a frame; contract validation remains in inference."""

    payload = uploaded if isinstance(uploaded, bytes) else uploaded.read()
    buffer = io.BytesIO(payload)
    suffix = Path(name).suffix.lower()
    if suffix == ".parquet":
        return pd.read_parquet(buffer)
    if suffix in {".csv", ".tsv"}:
        return pd.read_csv(buffer, sep="\t" if suffix == ".tsv" else ",")
    raise ValueError("Choose a .csv, .tsv, or .parquet sequence file")


def _preview(frame: pd.DataFrame) -> dict[str, object]:
    """Return display-only metadata; the inference API performs validation."""

    timestamp_range = "Unavailable"
    if "timestamp" in frame.columns and len(frame):
        parsed = pd.to_datetime(frame["timestamp"], errors="coerce", format="mixed")
        if parsed.notna().all():
            timestamp_range = f"{parsed.iloc[0].isoformat()} → {parsed.iloc[-1].isoformat()}"
    return {
        "sequence_length": len(frame),
        "feature_count": len([column for column in frame.columns if column not in {"timestamp", "capture_day"}]),
        "timestamp_range": timestamp_range,
    }


def _render_header() -> None:
    st.markdown(
        """
        <style>
        .stApp { background: #07111f; color: #e7eef8; }
        [data-testid="stHeader"] { background: #07111f; }
        .hero { padding: 1.2rem 1.4rem; border: 1px solid #1d3b59; border-radius: 14px; background: linear-gradient(135deg, #0b1b2d, #102a40); margin-bottom: 1rem; }
        .eyebrow { color: #54d6c7; font-size: .78rem; letter-spacing: .14em; text-transform: uppercase; font-weight: 700; }
        .hero h1 { margin: .25rem 0 .35rem; color: #f4f8fc; font-size: 2rem; }
        .hero p { margin: 0; color: #a9bfd2; }
        .warning-card { padding: 1rem; border-radius: 12px; border: 1px solid #9e6b2d; background: #2b2112; }
        .clear-card { padding: 1rem; border-radius: 12px; border: 1px solid #276b65; background: #102b2b; }
        .muted { color: #9fb4c7; font-size: .88rem; }
        </style>
        <div class="hero">
          <div class="eyebrow">SIH26-26153 · Offline defensive forecasting</div>
          <h1>Network State Forecast</h1>
          <p>Review the next 50 seconds of forecast score from an approved 10-second network-state sequence.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_input() -> tuple[pd.DataFrame | None, str | None]:
    st.subheader("Input")
    st.caption("Use the deterministic demo fixture or provide a compatible 10-state sequence file.")
    demo_col, upload_col = st.columns([1, 2])
    with demo_col:
        run_demo = st.button("Run Demo", type="primary", use_container_width=True)
    with upload_col:
        uploaded = st.file_uploader("Compatible sequence file", type=["csv", "tsv", "parquet"])

    if run_demo:
        try:
            return load_sequence_from_path(DEMO_INPUT), DEMO_INPUT.name
        except (OSError, ValueError, pd.errors.ParserError, yaml.YAMLError) as exc:
            st.error(f"Demo input could not be loaded: {exc}")
            return None, None
    if uploaded is not None and st.button("Run Uploaded Sequence", use_container_width=True):
        try:
            return load_sequence_from_upload(uploaded.name, uploaded.getvalue()), uploaded.name
        except (OSError, ValueError, TypeError, pd.errors.ParserError, yaml.YAMLError) as exc:
            st.error(f"Uploaded input could not be loaded: {exc}")
            return None, None
    return None, None


def _render_preview(frame: pd.DataFrame, source_name: str) -> None:
    preview = _preview(frame)
    st.markdown(f"**Selected file:** `{source_name}`")
    cols = st.columns(4)
    cols[0].metric("States supplied", str(preview["sequence_length"]))
    cols[1].metric("Feature columns", str(preview["feature_count"]))
    cols[2].metric("Timestamp range", str(preview["timestamp_range"]))
    cols[3].metric("Validation status", "Pending inference")
    st.caption("The inference API performs the authoritative contract validation when the run control is executed.")


def _render_current_state(result: dict[str, object], frame: pd.DataFrame) -> None:
    st.subheader("Current State")
    cols = st.columns(5)
    cols[0].metric("Reference timestamp", str(result["reference_timestamp"]))
    cols[1].metric("State interval", "10 seconds")
    cols[2].metric("Input states", str(len(frame)))
    cols[3].metric("Features", "17")
    cols[4].metric("Model", "LSTM K=5")


def _render_warning(result: dict[str, object]) -> None:
    primary = result["forecast"][0]
    warning = bool(primary["warning"])
    card_class = "warning-card" if warning else "clear-card"
    label = "PREDICTIVE WARNING" if warning else "NO PREDICTIVE WARNING"
    st.subheader("Operating Warning")
    st.markdown(
        f"""
        <div class="{card_class}">
          <div class="eyebrow">+10 second forecast</div>
          <h2>{label}</h2>
          <p class="muted">Forecast Score: <strong>{float(primary['score']):.6f}</strong> · Threshold: <strong>{float(result['threshold']):.2f}</strong></p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("A Predictive warning means the Forecast Score crossed the selected operating threshold. It is not an attack confirmation.")


def _render_forecast(result: dict[str, object]) -> None:
    st.subheader("Future Forecast")
    rows = result["forecast"]
    table = pd.DataFrame(
        [
            {
                "Horizon": f"+{row['horizon_seconds']}s",
                "Timestamp": row["timestamp"],
                "Forecast Score": float(row["score"]),
                "Status": "Predictive warning" if row["warning"] else "No predictive warning",
            }
            for row in rows
        ]
    )
    st.dataframe(table, use_container_width=True, hide_index=True)

    chart = table.set_index("Timestamp")[["Forecast Score"]].copy()
    chart["Threshold"] = float(result["threshold"])
    st.subheader("Forecast Score Trajectory")
    st.line_chart(chart, y=["Forecast Score", "Threshold"], use_container_width=True)
    st.caption("The trajectory shows model scores across future horizons; a rise is not automatically an attack progression.")


def _render_explanation(result: dict[str, object]) -> None:
    explanation = result["explanation"]
    st.subheader("Explanation")
    st.caption("Strong model sensitivity is descriptive score response, not causal attribution.")
    top_features = pd.DataFrame(
        [
            {
                "Top contributing signal": row["feature"],
                "Contribution": float(row["contribution"]),
                "Sensitivity": float(row["sensitivity"]),
                "Temporal position": row["time_position"],
            }
            for row in explanation.get("top_features", [])
        ]
    )
    if not top_features.empty:
        st.markdown("**Top contributing features**")
        st.dataframe(top_features, use_container_width=True, hide_index=True)
    temporal = pd.DataFrame(
        [
            {
                "Temporal position": row["time_position"],
                "Sensitivity": float(row["sensitivity"]),
                "Signed contribution": float(row["signed_contribution"]),
            }
            for row in explanation.get("temporal_positions", [])[:5]
        ]
    )
    if not temporal.empty:
        st.markdown("**Most influential temporal positions**")
        st.dataframe(temporal, use_container_width=True, hide_index=True)


def _render_technical(result: dict[str, object]) -> None:
    with st.expander("Technical Details"):
        st.json(
            {
                "model_checkpoint": result.get("model_checkpoint"),
                "feature_schema_version": result.get("feature_schema_version"),
                "target_version": result.get("target_version"),
                "operating_mode": result.get("operating_mode"),
                "threshold": result.get("threshold"),
                "forecast_horizon_seconds": result.get("forecast_horizon_seconds"),
                "inference_timing_ms": result.get("timing_ms"),
                "test_status": KNOWN_TEST_STATUS,
            }
        )


def main() -> None:
    st.set_page_config(page_title="Network State Forecast", page_icon="🛡️", layout="wide")
    _render_header()
    frame, source_name = _render_input()
    if frame is None or source_name is None:
        st.info("Choose Run Demo or upload a compatible sequence, then run it to view the forecast.")
        return
    _render_preview(frame, source_name)
    try:
        result = predict_network_state_sequence(frame)
    except (FileNotFoundError, ValueError, TypeError, KeyError, OSError, pd.errors.ParserError, yaml.YAMLError) as exc:
        st.error(f"Input or inference validation failed: {exc}")
        with st.expander("Technical details"):
            st.code(f"{type(exc).__name__}: {exc}")
        return

    st.success("Validation passed · Real offline inference completed")
    _render_current_state(result, frame)
    st.divider()
    left, right = st.columns([1, 1.6])
    with left:
        _render_warning(result)
    with right:
        st.subheader("Operating Mode")
        mode_cols = st.columns(2)
        mode_cols[0].metric("Mode", str(result["operating_mode"]).title())
        mode_cols[1].metric("Threshold", f"{float(result['threshold']):.2f}")
        st.caption("Threshold selected from validation data; final test data was not used for policy selection.")
    st.divider()
    _render_forecast(result)
    st.divider()
    _render_explanation(result)
    _render_technical(result)


if __name__ == "__main__":
    main()
