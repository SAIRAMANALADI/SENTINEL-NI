"""Offline Streamlit demo for the frozen network-state inference API."""

from __future__ import annotations

import io
import time
from html import escape
from pathlib import Path
from typing import BinaryIO

import pandas as pd
import streamlit as st
import yaml

from src.forecasting.inference import predict_network_state_sequence
from src.evaluation.mitigation_policy import recommendations_for_sources
from src.api.client import get_json, post_json
from src.streaming.realtime_engine import RealtimeEngine
from src.streaming.replay import iter_packet_replay_events, iter_replay_events
from src.streaming.source_activity import aggregate_source_activity
from src.streaming.source_forecast import prioritize_sources


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEMO_INPUT = PROJECT_ROOT / "data" / "samples" / "inference_demo_sequence.csv"
SOURCE_DEMO_INPUT = PROJECT_ROOT / "data" / "samples" / "source_attribution_mock.jsonl"


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
        .integrated-status { padding: 1.05rem 1.2rem; border-radius: 15px; border: 1px solid #ff6b61; background: linear-gradient(135deg, #351b25, #241622); box-shadow: 0 8px 24px rgba(255, 88, 77, .14); margin: .35rem 0 .8rem; }
        .integrated-status.clear { border-color: #3dc7b7; background: linear-gradient(135deg, #102e32, #12232f); box-shadow: 0 8px 24px rgba(61, 199, 183, .12); }
        .integrated-status .status-title { color: #fff4f2; font-size: clamp(1.65rem, 3vw, 2.35rem); font-weight: 800; letter-spacing: .01em; line-height: 1.05; margin: .25rem 0 .35rem; }
        .integrated-status.clear .status-title { color: #d9fff8; }
        .integrated-status .status-copy { color: #e9c7c3; font-size: .92rem; }
        .integrated-status.clear .status-copy { color: #b7e6df; }
        .summary-metric { min-height: 5.2rem; padding: .8rem .9rem; border: 1px solid #23445f; border-radius: 12px; background: #0b1b2b; }
        .summary-metric .label { color: #8ca9bf; font-size: .72rem; letter-spacing: .1em; text-transform: uppercase; font-weight: 700; }
        .summary-metric .value { color: #f5f8fb; font-size: 1.35rem; font-weight: 750; margin-top: .35rem; }
        .source-card { min-height: 9.5rem; padding: .85rem .9rem; border: 1px solid #294b64; border-radius: 12px; background: #0a1928; }
        .source-card.high { border-color: #ff725f; background: linear-gradient(145deg, #301b25, #121c2a); }
        .source-card.medium { border-color: #e0ad55; background: linear-gradient(145deg, #2b2418, #121c2a); }
        .source-card.low { border-color: #2a6370; }
        .source-card .rank { color: #62d7ca; font-size: .7rem; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }
        .source-card .source { color: #f2f7fb; font-size: 1.08rem; font-weight: 750; margin: .3rem 0; }
        .source-card .priority { color: #ffb6a9; font-size: .76rem; font-weight: 800; letter-spacing: .06em; }
        .source-card.low .priority { color: #8ddbd1; }
        .source-card.medium .priority { color: #f2c776; }
        .source-card .reason { color: #afc1d0; font-size: .78rem; line-height: 1.35; margin-top: .55rem; }
        .mitigation-card { min-height: 6.2rem; padding: .75rem .85rem; border-left: 3px solid #54d6c7; border-radius: 9px; background: #0b1b2b; }
        .mitigation-card.high { border-left-color: #ff725f; }
        .mitigation-card .source { color: #dbe8f1; font-weight: 750; font-size: .86rem; }
        .mitigation-card .action { color: #fff; font-size: .88rem; margin-top: .35rem; line-height: 1.25; }
        .mitigation-card .tag { color: #83a0b4; font-size: .68rem; letter-spacing: .09em; text-transform: uppercase; margin-top: .45rem; }
        .forecast-timeline { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: .55rem; margin: .3rem 0 .65rem; }
        .forecast-step { padding: .7rem .55rem; border: 1px solid #23445f; border-radius: 10px; background: #0a1928; text-align: center; }
        .forecast-step.primary { border-color: #ff725f; background: #2b1a25; }
        .forecast-step.warning { box-shadow: inset 0 -3px 0 #ff725f; }
        .forecast-step .horizon { color: #7fa6be; font-size: .7rem; font-weight: 800; letter-spacing: .08em; }
        .forecast-step .score { color: #f5f8fb; font-size: 1.15rem; font-weight: 750; margin-top: .25rem; }
        .forecast-step .decision { color: #ffad9f; font-size: .65rem; margin-top: .22rem; }
        .forecast-step:not(.warning) .decision { color: #8bcfc7; }
        .telemetry-strip { padding: .65rem .8rem; border: 1px solid #23445f; border-radius: 10px; background: #0a1928; }
        @media (max-width: 900px) { .forecast-timeline { gap: .3rem; } .forecast-step { padding: .55rem .25rem; } .forecast-step .score { font-size: .98rem; } }
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
    cols[2].metric("Input states", str(result.get("input_states", len(frame))))
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
                "policy_version": result.get("policy_version"),
                "operating_mode": result.get("operating_mode"),
                "threshold": result.get("threshold"),
                "forecast_horizon_seconds": result.get("forecast_horizon_seconds"),
                "inference_timing_ms": result.get("timing_ms"),
                "verification_status": "Verified locally",
            }
        )


def _render_source_prioritization(prioritized: pd.DataFrame, recommendations: list[dict[str, object]]) -> None:
    """Render the optional recommendation-only source-attribution sidecar."""

    st.subheader("SOURCE PRIORITIZATION")
    recommendation_by_source = {row["source_ip"]: row["recommendation"] for row in recommendations}
    rows = []
    for row in prioritized.to_dict(orient="records"):
        context = row.get("forecast_context") or {}
        forecast_context = "Elevated network forecast" if context.get("network_warning") else "No elevated network forecast"
        if not context.get("available"):
            forecast_context = "Network forecast unavailable"
        rows.append(
            {
                "Source": row["source_ip"],
                "Activity": (
                    f"{int(row['packet_count'])} packets · {float(row['byte_count']):.0f} bytes · "
                    f"{int(row['unique_destinations'])} destinations"
                ),
                "Forecast context": forecast_context,
                "Priority": row["priority"],
                "Recommended action": recommendation_by_source.get(row["source_ip"], "Monitor source"),
                "Measured reasons": row["measured_reasons"],
            }
        )
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption("Prototype source adapter: a high-priority source is a candidate source, not an attribution claim. No traffic is blocked.")


def _render_replay_mode() -> None:
    st.subheader("Demo Replay")
    st.caption("Replay uses the approved deterministic 10-state fixture and the same inference API as Static Sample.")
    controls = st.columns(3)
    speed = controls[0].number_input(
        "Replay speed factor",
        min_value=0.0,
        max_value=20.0,
        value=0.0,
        step=1.0,
        help="0 runs immediately. A positive value controls wall-clock sleep only; logical timestamps remain unchanged.",
    )
    max_states = controls[1].number_input("Maximum states", min_value=1, max_value=120, value=10, step=1)
    run_replay = controls[2].button("Start Replay", type="primary", use_container_width=True)
    show_source = st.checkbox("Show deterministic source-attribution mock", value=False)
    if not run_replay:
        st.info("Start Replay to emit validated 10-second states and trigger K=5 inference after state 10.")
        return

    status_placeholder = st.empty()
    engine = RealtimeEngine()
    previous_timestamp = None
    try:
        for update in engine.replay(iter_replay_events(DEMO_INPUT), max_states=int(max_states)):
            if speed > 0 and previous_timestamp is not None:
                time.sleep(10.0 / float(speed))
            previous_timestamp = update.timestamp
            if update.inference_result is None:
                status_placeholder.info(
                    f"{update.timestamp}: {update.status} — waiting for exactly 10 valid states"
                )
                continue
            result = update.inference_result
            status_placeholder.success(
                f"Replay state {update.state_index} complete at {update.timestamp} · "
                f"processing {update.processing_ms:.2f} ms"
            )
            _render_current_state(result, pd.DataFrame())
            _render_warning(result)
            _render_forecast(result)
            _render_explanation(result)
            if show_source:
                packet_events = list(iter_packet_replay_events(SOURCE_DEMO_INPUT))
                activity = aggregate_source_activity([event.payload for event in packet_events])
                prioritized = prioritize_sources(activity, result)
                _render_source_prioritization(
                    prioritized,
                    recommendations_for_sources(prioritized.to_dict(orient="records")),
                )
            _render_technical(result)
    except (FileNotFoundError, OSError, ValueError, TypeError, pd.errors.ParserError, yaml.YAMLError) as exc:
        status_placeholder.error(f"Replay validation failed: {exc}")


def _render_integrated_demo() -> None:
    # run_final_demo remains backend-owned; Streamlit calls only the API.
    st.subheader("Full Integrated Demo")
    st.caption("Backend API replay using deterministic DEMO / TEST DATA — NOT RESEARCH DATA.")
    if not st.button("RUN FULL DEMO", type="primary", use_container_width=True):
        st.info("Run the backend-mediated source → network state → forecast → mitigation demonstration.")
        return
    try:
        result = post_json("/api/v1/demo")
    except (OSError, RuntimeError, ValueError, TypeError, KeyError) as exc:
        st.error(f"BACKEND UNAVAILABLE — Full demo request failed: {exc}")
        return

    network = result["network_forecast"]
    display_result = {
        "forecast": network["forecasts"],
        "threshold": network["threshold"],
        "explanation": network["explanation"],
        "model_checkpoint": "models/lstm_multistep_k5.pt",
        "feature_schema_version": "network-state-v1.0",
        "target_version": "docs/TARGET_STATE_SPEC.md",
        "policy_version": "operating-policy-v1",
        "operating_mode": network["operating_mode"],
        "forecast_horizon_seconds": network["forecast_horizon_seconds"],
        "timing_ms": result["timing_ms"],
    }
    st.success("Full integrated backend demonstration completed")
    primary = network["forecasts"][0]
    status_class = "" if primary["warning"] else "clear"
    status_label = "Predictive warning" if primary["warning"] else "No predictive warning"
    st.markdown(
        f"""
        <div class="integrated-status {status_class}">
          <div class="eyebrow">NETWORK STATUS · PRIMARY +10 SECOND OUTLOOK</div>
          <div class="status-title">{escape(status_label)}</div>
          <div class="status-copy">Forecast Score {float(primary['score']):.6f} · Threshold {float(network['threshold']):.2f} · Balanced operating mode</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    metric_cols = st.columns(4)
    summary_metrics = [
        ("Forecast Score", f"{float(primary['score']):.6f}"),
        ("Threshold", f"{float(network['threshold']):.2f}"),
        ("Primary horizon", "+10 seconds"),
        ("Context", "L=10 · 10 states"),
    ]
    for column, (label, value) in zip(metric_cols, summary_metrics):
        column.markdown(
            f'<div class="summary-metric"><div class="label">{escape(label)}</div><div class="value">{escape(value)}</div></div>',
            unsafe_allow_html=True,
        )
    st.caption("Forecast Score is the raw model output; it is not a calibrated probability.")

    prioritized = pd.DataFrame(result["source_priorities"])
    recommendations = result["mitigation_recommendations"]
    st.subheader("Top Candidate Sources")
    source_cols = st.columns(max(1, min(3, len(prioritized))))
    for column, row in zip(source_cols, prioritized.to_dict(orient="records")):
        priority = str(row["priority"])
        priority_class = "high" if priority.startswith("HIGH") else "medium" if priority.startswith("MEDIUM") else "low"
        activity = row.get("activity_features", {})
        activity_text = (
            f"{int(activity.get('packet_count', row.get('packet_count', 0)))} packets · "
            f"{float(activity.get('byte_count', row.get('byte_count', 0))):.0f} bytes · "
            f"{int(activity.get('unique_destinations', row.get('unique_destinations', 0)))} destinations"
        )
        column.markdown(
            f"""
            <div class="source-card {priority_class}">
              <div class="rank">Rank {list(prioritized['source_ip']).index(row['source_ip']) + 1}</div>
              <div class="source">{escape(str(row['source_ip']))}</div>
              <div class="priority">{escape(priority)}</div>
              <div class="reason">{escape(str(row['measured_reasons']))}<br><span class="muted">{escape(activity_text)}</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.subheader("Mitigation Recommendations")
    mitigation_cols = st.columns(max(1, min(3, len(recommendations))))
    for column, recommendation in zip(mitigation_cols, recommendations):
        source_priority = next(
            (row["priority"] for row in prioritized.to_dict(orient="records") if row["source_ip"] == recommendation["source_ip"]),
            "LOW PRIORITY SOURCE",
        )
        priority_class = "high" if str(source_priority).startswith("HIGH") else ""
        column.markdown(
            f"""
            <div class="mitigation-card {priority_class}">
              <div class="source">{escape(str(recommendation['source_ip']))}</div>
              <div class="action">{escape(str(recommendation['recommendation']))}</div>
              <div class="tag">Simulation only · candidate source</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.caption("Recommendations are decision support only. No firewall, WAF, API gateway, or real traffic policy was changed.")

    st.subheader("Forecast Timeline")
    timeline = []
    for index, row in enumerate(network["forecasts"]):
        decision = "Warning" if row["warning"] else "No warning"
        classes = ["forecast-step"]
        if index == 0:
            classes.append("primary")
        if row["warning"]:
            classes.append("warning")
        timeline.append(
            f'<div class="{" ".join(classes)}"><div class="horizon">+{int(row["horizon_seconds"])}s</div><div class="score">{float(row["score"]):.6f}</div><div class="decision">{decision}</div></div>'
        )
    st.markdown(f'<div class="forecast-timeline">{"".join(timeline)}</div>', unsafe_allow_html=True)
    st.caption("The +10s card is the primary operating horizon; later scores are direct K=5 forecast outputs.")

    st.subheader("Forecast Score Trajectory")
    chart = pd.DataFrame(
        {
            "Forecast Score": [float(row["score"]) for row in network["forecasts"]],
            "Threshold": [float(network["threshold"])] * len(network["forecasts"]),
        },
        index=[f"+{int(row['horizon_seconds'])}s" for row in network["forecasts"]],
    )
    st.line_chart(chart, y=["Forecast Score", "Threshold"], use_container_width=True)

    _render_explanation(display_result)
    with st.expander("Technical Details"):
        st.json(
            {
                "state_count": result["state_count"],
                "history_length": result["history_length"],
                "processing_time_ms": result["processing_time_ms"],
                "timing_ms": result["timing_ms"],
                "simulation_only": result["simulation_only"],
                "pcap_attribution_validated": result["pcap_attribution_validated"],
            }
        )


def _render_live_forecast(forecast: dict[str, object], state: dict[str, object]) -> None:
    status = str(forecast.get("status", "WAITING_FOR_LIVE_HISTORY"))
    horizons = list(forecast.get("horizons") or [])
    if status == "WAITING_FOR_LIVE_HISTORY":
        st.info(
            f"WAITING FOR LIVE HISTORY · {int(state.get('buffer_size', 0))} / "
            f"{int(state.get('buffer_required', 10))} states"
        )
        return
    if status == "STALE_NOT_LIVE":
        st.warning("DATA STALE · last forecast is retained for review and is not current live data")
    if not horizons:
        st.info("WAITING FOR LIVE HISTORY")
        return

    primary = horizons[0]
    primary_warning = bool(primary.get("warning"))
    status_label = "Predictive warning" if primary_warning else "No predictive warning"
    status_class = "" if primary_warning else "clear"
    st.markdown(
        f"""
        <div class="integrated-status {status_class}">
          <div class="eyebrow">LIVE NETWORK STATUS · PRIMARY +10 SECOND OUTLOOK</div>
          <div class="status-title">{escape(status_label)}</div>
          <div class="status-copy">Forecast Score {float(primary['score']):.6f} · Threshold {float(forecast.get('threshold') or 0):.2f}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    metric_cols = st.columns(4)
    for column, label, value in zip(
        metric_cols,
        ("Forecast Score", "Threshold", "Primary horizon", "Reference timestamp"),
        (
            f"{float(primary['score']):.6f}",
            f"{float(forecast.get('threshold') or 0):.2f}",
            "+10 seconds",
            str(forecast.get("reference_timestamp") or "Unavailable"),
        ),
    ):
        column.markdown(
            f'<div class="summary-metric"><div class="label">{escape(label)}</div><div class="value">{escape(value)}</div></div>',
            unsafe_allow_html=True,
        )
    st.caption("Forecast Score is the raw model output; it is not a calibrated probability.")

    st.subheader("Forecast Timeline")
    timeline = []
    for index, row in enumerate(horizons):
        warning = bool(row.get("warning"))
        classes = ["forecast-step"]
        if index == 0:
            classes.append("primary")
        if warning:
            classes.append("warning")
        decision = "Warning" if warning else "No warning"
        timeline.append(
            f'<div class="{" ".join(classes)}"><div class="horizon">+{int(row["horizon_seconds"])}s</div><div class="score">{float(row["score"]):.6f}</div><div class="decision">{decision}</div></div>'
        )
    st.markdown(f'<div class="forecast-timeline">{"".join(timeline)}</div>', unsafe_allow_html=True)
    chart = pd.DataFrame(
        {
            "Forecast Score": [float(row["score"]) for row in horizons],
            "Threshold": [float(forecast.get("threshold") or 0)] * len(horizons),
        },
        index=[f"+{int(row['horizon_seconds'])}s" for row in horizons],
    )
    st.line_chart(chart, y=["Forecast Score", "Threshold"], use_container_width=True)
    with st.expander("Explanation"):
        st.json(forecast.get("explanation") or {})


def _render_live_sources(source_priorities: list[dict[str, object]], mitigation: dict[str, object]) -> None:
    st.subheader("Source Priority")
    if not source_priorities:
        st.caption("No current candidate-source activity is available.")
    else:
        columns = st.columns(max(1, min(3, len(source_priorities[:6]))))
        for column, row in zip(columns, source_priorities[:6]):
            priority = str(row.get("priority", "LOW PRIORITY SOURCE"))
            priority_class = "high" if priority.startswith("HIGH") else "medium" if priority.startswith("MEDIUM") else "low"
            column.markdown(
                f"""
                <div class="source-card {priority_class}">
                  <div class="source">{escape(str(row.get('source_ip', 'Unknown source')))}</div>
                  <div class="priority">{escape(priority)}</div>
                  <div class="reason">{escape(str(row.get('measured_reasons', 'Measured activity only')))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    st.caption("Candidate-source priority is based on measured activity. It is not attacker attribution.")

    st.subheader("Mitigation")
    st.caption("Simulation only: TRUE · Recommendation only — no traffic is automatically blocked.")
    recommendations = list(mitigation.get("recommendations") or [])
    if recommendations:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "Source": row.get("source_ip"),
                        "Priority": row.get("priority"),
                        "Recommendation": row.get("recommendation"),
                        "Simulation only": row.get("simulation_only", True),
                    }
                    for row in recommendations[:6]
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.caption("No mitigation recommendation is currently available.")


@st.fragment(run_every="2s")
def _render_live_runtime() -> None:
    try:
        live = get_json("/api/v1/live")
    except (OSError, RuntimeError, ValueError, TypeError, KeyError) as exc:
        st.error(f"BACKEND UNAVAILABLE — live runtime state could not be read: {exc}")
        return

    telemetry = dict(live.get("telemetry") or {})
    state = dict(live.get("state") or {})
    status = str(telemetry.get("status", "UNKNOWN"))
    mode = str(telemetry.get("mode", "unknown")).upper()
    interface = str(telemetry.get("interface") or "Not configured")
    event_count = int(telemetry.get("event_count", 0))
    flow_count = int(telemetry.get("flow_count", 0))
    last_event = str(telemetry.get("last_event_at") or "No event received")
    freshness = str(telemetry.get("freshness", "DATA STALE"))
    readiness = str(telemetry.get("readiness_state", "STOPPED"))
    readiness_labels = {
        "INITIALIZING": "INITIALIZING",
        "CAPTURING": "CAPTURING",
        "BUILDING_FLOW_HISTORY": "BUILDING FLOW HISTORY",
        "BUILDING_NETWORK_HISTORY": "BUILDING NETWORK HISTORY",
        "FORECAST_READY": "FORECAST READY",
        "STALE": "STALE",
        "STOPPED": "STOPPED",
        "ERROR": "ERROR",
    }
    valid_states = int(state.get("valid_state_count", 0))
    required_states = int(state.get("buffer_required", 10))
    cols = st.columns(6)
    for column, label, value in zip(
        cols,
        ("Telemetry", "Interface", "Status", "Events", "Flows", "Last event"),
        (mode, interface, status, str(event_count), str(flow_count), last_event),
    ):
        column.markdown(
            f'<div class="telemetry-strip"><div class="label">{escape(label)}</div><strong>{escape(value)}</strong></div>',
            unsafe_allow_html=True,
        )
    st.caption(f"{freshness} · valid states {valid_states} / {required_states} required")
    if readiness == "BUILDING_NETWORK_HISTORY":
        st.info(f"BUILDING NETWORK HISTORY · {valid_states} / {required_states} states")
    elif readiness == "FORECAST_READY":
        st.success("FORECAST READY")
    elif readiness == "STALE":
        st.warning("STALE · capture stopped; the last forecast is not current live data")
    elif readiness == "ERROR":
        st.error("ERROR · live capture or runtime processing needs attention")
    else:
        st.caption(f"Readiness: {readiness_labels.get(readiness, readiness)}")

    packet_quality = dict(telemetry.get("packet_quality") or {})
    with st.expander("PACKET QUALITY & TECHNICAL DETAILS"):
        quality_cols = st.columns(4)
        quality_values = (
            ("Packets seen", packet_quality.get("packets_seen", 0)),
            ("Valid events", packet_quality.get("valid_events", 0)),
            ("Ignored / unsupported", packet_quality.get("ignored_events", 0)),
            ("Valid rate", f"{float(packet_quality.get('valid_percentage', 0.0)):.2f}%"),
        )
        for column, (label, value) in zip(quality_cols, quality_values):
            column.metric(label, value)
        categories = packet_quality.get("ignored_categories") or {}
        st.caption(
            "Ignored rate: "
            f"{float(packet_quality.get('ignored_percentage', 0.0)):.2f}% · "
            f"dropped events: {int(packet_quality.get('dropped_events', 0))}"
        )
        if categories:
            st.json(categories)
        startup_timing = live.get("startup_timing") or {}
        if startup_timing:
            st.json(startup_timing)

    if mode == "LIVE":
        st.warning("LIVE NETWORK TELEMETRY reads metadata from the configured interface. Capture does not store payload contents.")
        controls = st.columns(2)
        if controls[0].button("START LIVE CAPTURE", disabled=status == "LIVE_RUNNING", use_container_width=True):
            try:
                post_json("/api/v1/telemetry/start", timeout=10)
                st.rerun()
            except (OSError, RuntimeError, ValueError, TypeError, KeyError) as exc:
                st.error(f"Live capture could not start: {exc}")
        if controls[1].button("STOP LIVE CAPTURE", disabled=status != "LIVE_RUNNING", use_container_width=True):
            try:
                post_json("/api/v1/telemetry/stop", timeout=10)
                st.rerun()
            except (OSError, RuntimeError, ValueError, TypeError, KeyError) as exc:
                st.error(f"Live capture could not stop: {exc}")
    else:
        st.caption("Live capture is disabled. The backend is using an explicit non-live telemetry mode.")

    _render_live_forecast(dict(live.get("forecast") or {}), state)
    _render_live_sources(list(live.get("source_priorities") or []), dict(live.get("mitigation") or {}))
    if live.get("last_error"):
        with st.expander("Technical Details"):
            st.code(str(live["last_error"]))


def _render_telemetry_controls() -> None:
    """Render API-owned live telemetry, state, forecast, and policy outputs."""

    st.subheader("Live Network Telemetry")
    _render_live_runtime()


def main() -> None:
    st.set_page_config(page_title="Network State Forecast", page_icon="🛡️", layout="wide")
    _render_header()
    mode = st.radio("Input mode", ["LIVE", "REPLAY", "MOCK / STATIC", "Full Integrated Demo"], horizontal=True)
    st.caption(
        {
            "LIVE": "LIVE · REAL CAPTURE",
            "REPLAY": "REPLAY · DETERMINISTIC REPLAY",
            "MOCK / STATIC": "MOCK / STATIC · DEMO / TEST DATA",
            "Full Integrated Demo": "FULL INTEGRATED DEMO · BACKEND-MEDIATED DEMO / TEST DATA",
        }[mode]
    )
    if mode == "LIVE":
        _render_telemetry_controls()
        return
    if mode == "Full Integrated Demo":
        _render_integrated_demo()
        return
    if mode == "REPLAY":
        _render_replay_mode()
        return
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
