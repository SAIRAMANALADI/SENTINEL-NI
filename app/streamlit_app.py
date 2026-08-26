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
        :root { --ink: #f4f7fb; --muted: #8d9eaf; --line: #223243; --surface: #0e1823; --surface-2: #111e2b; --cyan: #67d7cb; --amber: #e9b45f; --red: #ff7569; --green: #72d19b; }
        .stApp { background: #080d14; color: var(--ink); }
        [data-testid="stHeader"] { background: #080d14; }
        [data-testid="stSidebar"] { background: #0a111a; border-right: 1px solid #182532; }
        [data-testid="stSidebar"] > div:first-child { padding-top: 1.15rem; }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: var(--muted); }
        [data-testid="stRadio"] label { color: #c4d0dc; font-size: .82rem; }
        [data-testid="stBaseButton-primary"] { background: #d8a35d !important; border-color: #e5b873 !important; color: #0b1219 !important; }
        [data-testid="stBaseButton-primary"] p { color: #0b1219 !important; font-weight: 800 !important; }
        [data-testid="stBaseButton-primary"]:hover { background: #e7b873 !important; border-color: #f2cc91 !important; }
        .block-container { max-width: 1420px; padding: 1.25rem 2.4rem 3rem; }
        .brand-lockup { padding: .2rem .1rem 1.25rem; border-bottom: 1px solid #1c2b39; margin-bottom: 1rem; }
        .brand-mark { color: var(--cyan); font-size: .7rem; font-weight: 800; letter-spacing: .19em; text-transform: uppercase; }
        .brand-name { color: #f4f7fb; font-size: 1.22rem; letter-spacing: -.03em; font-weight: 750; margin-top: .25rem; }
        .brand-sub { color: #718496; font-size: .7rem; letter-spacing: .08em; text-transform: uppercase; margin-top: .25rem; }
        .shell-header { display:flex; justify-content:space-between; align-items:flex-start; gap:1rem; padding: .15rem 0 1rem; border-bottom: 1px solid #1b2936; margin-bottom: 1rem; }
        .shell-kicker, .eyebrow { color: var(--cyan); font-size: .68rem; letter-spacing: .16em; text-transform: uppercase; font-weight: 800; }
        .shell-title { color: #f7f9fc; font-size: clamp(1.45rem, 2.7vw, 2.25rem); letter-spacing: -.055em; font-weight: 760; line-height: 1.05; margin: .28rem 0 .35rem; }
        .shell-copy { color: #91a3b4; font-size: .88rem; max-width: 660px; line-height: 1.45; }
        .header-status { display:flex; align-items:center; gap:.55rem; color:#c8d5df; font-size:.76rem; white-space:nowrap; padding-top:.25rem; }
        .status-dot { width:.52rem; height:.52rem; border-radius:50%; background:var(--green); box-shadow:0 0 0 4px rgba(114,209,155,.09); }
        .section-head { display:flex; justify-content:space-between; align-items:baseline; gap:1rem; margin: 1.8rem 0 .75rem; }
        .section-title { color:#eff4f8; font-size:1rem; font-weight:750; letter-spacing:-.02em; margin:0; }
        .section-meta { color:#708497; font-size:.72rem; }
        .panel { border:1px solid var(--line); border-radius:14px; background:linear-gradient(145deg, #101b27, #0c151f); padding:1.05rem 1.15rem; }
        .panel-tight { padding:.82rem .95rem; }
        .hero-panel { border:1px solid #4a3038; border-radius:16px; background:linear-gradient(130deg, #221923, #111923 68%); padding:1.15rem 1.25rem; min-height:10.4rem; }
        .hero-panel.clear { border-color:#28544f; background:linear-gradient(130deg, #122623, #101b24 68%); }
        .hero-label { color:#b8c6d0; font-size:.68rem; letter-spacing:.13em; text-transform:uppercase; font-weight:800; }
        .hero-status { color:#fff4f1; font-size:clamp(1.8rem, 4vw, 3rem); font-weight:800; letter-spacing:-.06em; line-height:1; margin:.5rem 0 .65rem; }
        .hero-panel.clear .hero-status { color:#d9fff5; }
        .hero-score { color:#f8fafc; font-variant-numeric:tabular-nums; font-size:clamp(2.1rem, 5vw, 3.7rem); font-weight:780; letter-spacing:-.065em; }
        .hero-score-label { color:#8da1b1; font-size:.7rem; letter-spacing:.12em; text-transform:uppercase; margin-top:.25rem; }
        .hero-foot { display:flex; gap:1.2rem; flex-wrap:wrap; color:#91a5b5; font-size:.78rem; margin-top:1rem; }
        .hero-foot strong { color:#e7eef5; font-weight:650; }
        .metric-rail { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.6rem; }
        .metric-cell { border:1px solid var(--line); border-radius:11px; background:#0d1721; padding:.78rem .85rem; min-height:4.7rem; }
        .metric-label { color:#718699; font-size:.64rem; letter-spacing:.12em; text-transform:uppercase; font-weight:800; }
        .metric-value { color:#f1f5f8; font-size:1.05rem; font-weight:720; font-variant-numeric:tabular-nums; margin-top:.42rem; }
        .metric-note { color:#7f93a5; font-size:.69rem; margin-top:.18rem; }
        .forecast-timeline { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:.5rem; margin:.25rem 0 .8rem; }
        .forecast-step { position:relative; padding:.78rem .65rem .72rem; border:1px solid var(--line); border-radius:11px; background:#0d1721; text-align:left; overflow:hidden; }
        .forecast-step.primary { border-color:#657c91; background:#122130; }
        .forecast-step.warning { border-bottom:2px solid var(--amber); }
        .forecast-step.primary.warning { border-color:#a26d4d; background:#241b1c; }
        .forecast-step .horizon { color:#8ca3b5; font-size:.66rem; font-weight:800; letter-spacing:.1em; }
        .forecast-step .score { color:#f4f7fa; font-size:1.2rem; font-weight:760; font-variant-numeric:tabular-nums; letter-spacing:-.035em; margin-top:.4rem; }
        .forecast-step .decision { color:#81d4bb; font-size:.63rem; margin-top:.2rem; }
        .forecast-step.warning .decision { color:#f3bd75; }
        .forecast-threshold { color:#73899a; font-size:.7rem; }
        .source-card { min-height:10rem; padding:1rem; border:1px solid var(--line); border-radius:13px; background:#0d1721; }
        .source-card.high { border-color:#a45e58; background:linear-gradient(145deg,#26191d,#101923); }
        .source-card.medium { border-color:#80663f; background:linear-gradient(145deg,#211d17,#101923); }
        .source-card.low { border-color:#2e5961; }
        .source-card .rank { color:#6f899c; font-size:.63rem; font-weight:850; letter-spacing:.14em; text-transform:uppercase; }
        .source-card .source { color:#f2f6f9; font-size:1.05rem; font-weight:750; margin:.48rem 0 .3rem; font-variant-numeric:tabular-nums; }
        .source-card .priority { color:#ffad9e; font-size:.68rem; font-weight:850; letter-spacing:.1em; }
        .source-card.low .priority { color:#82d6c7; }
        .source-card.medium .priority { color:#efc477; }
        .source-card .reason { color:#acbdca; font-size:.76rem; line-height:1.42; margin-top:.72rem; }
        .source-card .evidence { color:#7f96a7; font-size:.7rem; line-height:1.4; margin-top:.52rem; }
        .mitigation-card { min-height:6.2rem; padding:.9rem 1rem; border:1px solid #294253; border-left:3px solid var(--cyan); border-radius:11px; background:#0d1721; }
        .mitigation-card.high { border-left-color:var(--red); border-color:#4f3437; }
        .mitigation-card .source { color:#eef3f7; font-weight:740; font-size:.84rem; }
        .mitigation-card .action { color:#d2dee6; font-size:.82rem; margin-top:.42rem; line-height:1.32; }
        .mitigation-card .tag { color:#7690a1; font-size:.62rem; letter-spacing:.1em; text-transform:uppercase; margin-top:.58rem; }
        .timeline-flow { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:.35rem; }
        .timeline-node { position:relative; padding:.72rem .65rem; border-top:2px solid #315160; background:#0d1721; border-radius:0 0 9px 9px; }
        .timeline-node .node-num { color:var(--cyan); font-size:.61rem; font-weight:850; letter-spacing:.12em; }
        .timeline-node .node-label { color:#d7e2e9; font-size:.72rem; margin-top:.38rem; }
        .timeline-node .node-copy { color:#73899a; font-size:.64rem; margin-top:.18rem; }
        .explain-lead { border-left:2px solid var(--cyan); padding:.6rem .8rem; background:#0d1721; border-radius:0 9px 9px 0; }
        .explain-feature { color:#f1f6f8; font-size:1.08rem; font-weight:740; margin-top:.28rem; }
        .explain-value { color:var(--cyan); font-size:.8rem; font-variant-numeric:tabular-nums; margin-top:.22rem; }
        .disclaimer { color:#7f93a4; font-size:.72rem; line-height:1.45; }
        .telemetry-strip { padding:.72rem .8rem; border:1px solid var(--line); border-radius:10px; background:#0d1721; min-height:4.6rem; }
        .telemetry-strip .label { color:#718699; font-size:.63rem; letter-spacing:.11em; text-transform:uppercase; font-weight:800; }
        .telemetry-strip strong { color:#ecf3f7; display:block; font-size:.88rem; margin-top:.42rem; overflow-wrap:anywhere; }
        .mode-pill { display:inline-block; padding:.26rem .5rem; border-radius:99px; border:1px solid #2c5f5e; color:#8de0cf; background:#102725; font-size:.62rem; font-weight:800; letter-spacing:.11em; }
        .simulation-banner { display:flex; justify-content:space-between; gap:1rem; align-items:center; padding:.58rem .8rem; border:1px solid #3e4b56; border-radius:9px; background:#0c151e; color:#a8bac6; font-size:.7rem; }
        .simulation-banner strong { color:#f0c477; letter-spacing:.08em; }
        .command-grid { display:grid; grid-template-columns:minmax(0,1.55fr) minmax(260px,.8fr); gap:.7rem; align-items:stretch; }
        .watch-panel { border:1px solid var(--line); border-radius:14px; background:#0d1721; padding:1rem; }
        .watch-row { display:grid; grid-template-columns:1.6rem 1fr auto; gap:.5rem; align-items:center; padding:.58rem 0; border-bottom:1px solid #1c2a37; }
        .watch-row:last-child { border-bottom:0; }
        .watch-rank { color:#6d889b; font-size:.62rem; font-weight:850; }
        .watch-source { color:#eaf1f5; font-size:.78rem; font-weight:720; }
        .watch-meta { color:#718899; font-size:.63rem; margin-top:.18rem; }
        .watch-priority { color:#ffad9e; font-size:.6rem; font-weight:850; letter-spacing:.08em; text-align:right; }
        .watch-priority.low { color:#82d6c7; }
        .watch-priority.medium { color:#efc477; }
        .watch-callout { margin-top:.8rem; padding:.65rem .7rem; border-left:2px solid var(--amber); background:#171a1d; color:#c9d5dc; font-size:.7rem; line-height:1.35; }
        @media (max-width: 900px) { .command-grid { grid-template-columns:1fr; } }
        @media (max-width: 900px) { .block-container { padding-left:1rem; padding-right:1rem; } .metric-rail { grid-template-columns:repeat(2,minmax(0,1fr)); } .timeline-flow { grid-template-columns:repeat(2,minmax(0,1fr)); } }
        @media (max-width: 620px) { .shell-header { display:block; } .header-status { margin-top:.8rem; } .forecast-timeline { gap:.28rem; } .forecast-step { padding:.62rem .38rem; } .forecast-step .score { font-size:.98rem; } .timeline-flow { grid-template-columns:1fr; } }
        </style>
        <div class="brand-lockup">
          <div class="brand-mark">SIH26-26153 / security intelligence</div>
          <div class="brand-name">SENTINEL <span style="color:#6c8496">/</span> NETWORK INTELLIGENCE</div>
          <div class="brand-sub">Network-state forecasting command center</div>
        </div>
        <div class="shell-header">
          <div>
            <div class="shell-kicker">Operations workspace</div>
            <div class="shell-title">See the next network state before it arrives.</div>
            <div class="shell-copy">A controlled forecast surface for analyst review, source prioritization, and recommendation-only response.</div>
          </div>
          <div class="header-status"><span class="status-dot"></span><span>MODEL SERVICE / OPERATIONAL</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _section(title: str, meta: str | None = None) -> None:
    suffix = f'<span class="section-meta">{escape(meta)}</span>' if meta else ""
    st.markdown(
        f'<div class="section-head"><div class="section-title">{escape(title)}</div>{suffix}</div>',
        unsafe_allow_html=True,
    )


def _metric_rail(items: list[tuple[str, str, str]]) -> None:
    cells = []
    for label, value, note in items:
        cells.append(
            f'<div class="metric-cell"><div class="metric-label">{escape(label)}</div>'
            f'<div class="metric-value">{escape(value)}</div><div class="metric-note">{escape(note)}</div></div>'
        )
    st.markdown(f'<div class="metric-rail">{"".join(cells)}</div>', unsafe_allow_html=True)


def _render_forecast_timeline(rows: list[dict[str, object]], threshold: float) -> None:
    timeline = []
    for index, row in enumerate(rows):
        warning = bool(row.get("warning"))
        classes = ["forecast-step"]
        if index == 0:
            classes.append("primary")
        if warning:
            classes.append("warning")
        decision = "Predictive warning" if warning else "No predictive warning"
        timeline.append(
            f'<div class="{" ".join(classes)}"><div class="horizon">+{int(row["horizon_seconds"])}s'
            f'{" · PRIMARY" if index == 0 else ""}</div><div class="score">{float(row["score"]):.4f}</div>'
            f'<div class="decision">{decision}</div></div>'
        )
    st.markdown(f'<div class="forecast-timeline">{"".join(timeline)}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="forecast-threshold">Operating threshold <strong>{float(threshold):.2f}</strong> · '
        'scores are raw model outputs, not a calibrated probability</div>',
        unsafe_allow_html=True,
    )


def _render_forecast_chart(rows: list[dict[str, object]], threshold: float) -> None:
    chart = pd.DataFrame(
        {
            "Forecast Score": [float(row["score"]) for row in rows],
            "Threshold": [float(threshold)] * len(rows),
        },
        index=[f'+{int(row["horizon_seconds"])}s' for row in rows],
    )
    st.line_chart(chart, y=["Forecast Score", "Threshold"], use_container_width=True, height=220)


def _render_operational_status(
    *,
    warning: bool,
    score: float,
    threshold: float,
    context: str,
    reference_timestamp: str,
) -> None:
    status_label = "Predictive warning" if warning else "No predictive warning"
    status_class = "" if warning else "clear"
    st.markdown(
        f'''
        <div class="hero-panel {status_class}">
          <div class="hero-label">Primary operating outlook · +10 seconds</div>
          <div class="hero-status">{escape(status_label)}</div>
          <div class="hero-score">{float(score):.4f}</div>
          <div class="hero-score-label">Forecast Score</div>
          <div class="hero-foot"><span>Threshold <strong>{float(threshold):.2f}</strong></span>
          <span>Reference <strong>{escape(reference_timestamp)}</strong></span>
          <span>{escape(context)}</span></div>
        </div>
        ''',
        unsafe_allow_html=True,
    )


def _render_system_timeline(items: list[tuple[str, str]]) -> None:
    nodes = []
    for index, (label, copy) in enumerate(items, start=1):
        nodes.append(
            f'<div class="timeline-node"><div class="node-num">0{index}</div>'
            f'<div class="node-label">{escape(label)}</div><div class="node-copy">{escape(copy)}</div></div>'
        )
    st.markdown(f'<div class="timeline-flow">{"".join(nodes)}</div>', unsafe_allow_html=True)


def _render_explanation_panel(explanation: dict[str, object]) -> None:
    top_features = list(explanation.get("top_features") or [])
    temporal = list(explanation.get("temporal_positions") or [])
    _section("Why this forecast?", "model sensitivity / not causal explanation")
    if top_features:
        lead = top_features[0]
        st.markdown(
            f'<div class="explain-lead"><div class="eyebrow">Top contributing signal</div>'
            f'<div class="explain-feature">{escape(str(lead.get("feature", "Unavailable")))}</div>'
            f'<div class="explain-value">Sensitivity {float(lead.get("sensitivity", 0.0)):.4f} · '
            f'{escape(str(lead.get("time_position", "current state")))}</div></div>',
            unsafe_allow_html=True,
        )
        if len(top_features) > 1:
            signal_text = " · ".join(str(row.get("feature", "Unavailable")) for row in top_features[1:4])
            st.caption(f"Other important signals · {signal_text}")
    if temporal:
        temporal_frame = pd.DataFrame(
            [
                {"Position": row.get("time_position"), "Sensitivity": float(row.get("sensitivity", 0.0))}
                for row in temporal[:5]
            ]
        ).set_index("Position")
        st.caption("Temporal contribution across the L=10 input history")
        st.bar_chart(temporal_frame, y="Sensitivity", height=150)
    st.markdown(
        '<div class="disclaimer">MODEL SENSITIVITY — NOT CAUSAL EXPLANATION. '
        'A high-sensitivity signal does not establish an attack cause or source identity.</div>',
        unsafe_allow_html=True,
    )


def _render_source_cards(prioritized: list[dict[str, object]], limit: int = 3) -> None:
    rows = prioritized[:limit]
    if not rows:
        st.caption("No current candidate-source activity is available.")
        return
    source_cols = st.columns(min(3, len(rows)))
    for index, (column, row) in enumerate(zip(source_cols, rows), start=1):
        priority = str(row.get("priority", "LOW PRIORITY SOURCE"))
        priority_class = "high" if priority.startswith("HIGH") else "medium" if priority.startswith("MEDIUM") else "low"
        activity = row.get("activity_features") or row
        evidence = (
            f'{int(activity.get("packet_count", 0))} packets · '
            f'{float(activity.get("byte_count", 0.0)):.0f} bytes · '
            f'{int(activity.get("unique_destinations", 0))} destinations'
        )
        column.markdown(
            f'<div class="source-card {priority_class}"><div class="rank">Rank {index:02d} · candidate source</div>'
            f'<div class="source">{escape(str(row.get("source_ip", "Unavailable")))}</div>'
            f'<div class="priority">{escape(priority)}</div>'
            f'<div class="reason">{escape(str(row.get("measured_reasons", "Measured activity only")))}</div>'
            f'<div class="evidence">{escape(evidence)}</div></div>',
            unsafe_allow_html=True,
        )


def _render_mitigation_cards(recommendations: list[dict[str, object]], prioritized: list[dict[str, object]]) -> None:
    if not recommendations:
        st.caption("No mitigation recommendation is currently available.")
        return
    priority_by_source = {str(row.get("source_ip")): str(row.get("priority", "")) for row in prioritized}
    cards = st.columns(min(3, len(recommendations)))
    for column, row in zip(cards, recommendations[:3]):
        source = str(row.get("source_ip", "Unavailable"))
        priority = priority_by_source.get(source, str(row.get("priority", "LOW PRIORITY SOURCE")))
        priority_class = "high" if priority.startswith("HIGH") else ""
        column.markdown(
            f'<div class="mitigation-card {priority_class}"><div class="source">{escape(source)} · '
            f'{escape(priority)}</div><div class="action">{escape(str(row.get("recommendation", "Monitor source")))}</div>'
            '<div class="tag">Simulation only · automatic blocking disabled</div></div>',
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
    _section("Current network state", "approved input contract")
    _metric_rail(
        [
            ("Reference timestamp", str(result["reference_timestamp"]), "forecast origin"),
            ("State interval", "10 seconds", "frozen cadence"),
            ("Input states", str(result.get("input_states", len(frame))), "L=10 context"),
            ("Features", "17", "frozen schema"),
        ]
    )


def _render_warning(result: dict[str, object]) -> None:
    primary = result["forecast"][0]
    _section("Operating warning", "primary +10 second horizon")
    _render_operational_status(
        warning=bool(primary["warning"]),
        score=float(primary["score"]),
        threshold=float(result["threshold"]),
        context=f'{result.get("operating_mode", "configured")} operating mode',
        reference_timestamp=str(result.get("reference_timestamp", "Unavailable")),
    )
    st.caption("A Predictive warning means the Forecast Score crossed the selected operating threshold. It is not an attack confirmation.")


def _render_forecast(result: dict[str, object]) -> None:
    rows = result["forecast"]
    _section("Future forecast", "+10s primary · +20s to +50s context")
    _render_forecast_timeline(rows, float(result["threshold"]))
    _section("Forecast Score Trajectory", "raw score against operating threshold")
    _render_forecast_chart(rows, float(result["threshold"]))
    st.caption("The trajectory shows model scores across future horizons; a rise is not automatically an attack progression.")


def _render_explanation(result: dict[str, object]) -> None:
    _render_explanation_panel(result["explanation"])


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

    _section("Source intelligence", "ranked candidate sources")
    _render_source_cards(prioritized.to_dict(orient="records"))
    _section("Recommended response", "advisory action only")
    _render_mitigation_cards(recommendations, prioritized.to_dict(orient="records"))
    st.caption("A high-priority source is a candidate source, not an attribution claim. No traffic is blocked.")


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
    _section("Full Integrated Demo", "controlled replay / backend-mediated")
    st.markdown(
        '<div class="simulation-banner"><span><strong>SIMULATION ONLY: TRUE</strong> · '
        'Deterministic demo fixture, not live telemetry or research data.</span>'
        '<span class="mode-pill">OPERATOR REVIEW</span></div>',
        unsafe_allow_html=True,
    )
    if not st.button("RUN FULL DEMO", type="primary", use_container_width=True):
        st.caption("Run the backend-mediated source → network state → forecast → mitigation demonstration.")
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
    primary = network["forecasts"][0]
    prioritized = pd.DataFrame(result["source_priorities"])
    recommendations = result["mitigation_recommendations"]
    _render_operational_status(
        warning=bool(primary["warning"]),
        score=float(primary["score"]),
        threshold=float(network["threshold"]),
        context="Balanced operating mode · 10-state context",
        reference_timestamp=str(network["reference_timestamp"]),
    )
    _section("Network telemetry", "demo fixture coverage")
    _metric_rail(
        [
            ("Network state", str(result["network_status"]), "current operating output"),
            ("Valid states", str(result["state_count"]), "10 required for L=10"),
            ("Candidate sources", str(len(prioritized)), "measured activity only"),
            ("Processing", f'{float(result["processing_time_ms"]):.0f} ms', "backend execution"),
        ]
    )

    _section("Forecast horizon", "+10s is the primary operating view")
    _render_forecast_timeline(network["forecasts"], float(network["threshold"]))
    _section("Forecast Score Trajectory", "direct K=5 outputs")
    _render_forecast_chart(network["forecasts"], float(network["threshold"]))

    left, right = st.columns([1.55, 1], gap="large")
    with left:
        _section("Source intelligence", "ranked candidate sources")
        _render_source_cards(prioritized.to_dict(orient="records"))
        st.caption("Priority is based on measured activity and forecast context. A candidate source is not a confirmed attacker; no traffic is automatically blocked.")
    with right:
        _section("Recommended response", "advisory action only")
        _render_mitigation_cards(recommendations, prioritized.to_dict(orient="records"))
        st.caption("No firewall, WAF, API gateway, or real traffic policy was changed.")

    _section("System timeline", "how the result was produced")
    _render_system_timeline(
        [
            ("Telemetry received", "deterministic event fixture"),
            ("Network state", "10-second aggregation"),
            ("Forecast calculated", "L=10 · K=5 LSTM"),
            ("Sources prioritized", f"{len(prioritized)} candidate sources"),
            ("Response recommended", "simulation only"),
        ]
    )
    _render_explanation_panel(network["explanation"])
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
        filled = int(state.get("buffer_size", 0))
        required = int(state.get("buffer_required", 10))
        st.markdown(
            f'<div class="panel"><div class="eyebrow">Forecast engine / preparing</div>'
            f'<div class="section-title" style="margin-top:.4rem">BUILDING FORECAST HISTORY</div>'
            f'<div class="hero-foot"><span>Valid states <strong>{filled} / {required}</strong></span>'
            '<span>Forecast becomes available after sufficient valid state history.</span></div></div>',
            unsafe_allow_html=True,
        )
        return
    if status == "STALE_NOT_LIVE":
        st.markdown(
            '<div class="panel" style="border-color:#80663f"><div class="eyebrow" style="color:#e9b45f">Data freshness</div>'
            '<div class="section-title" style="margin-top:.4rem">DATA STALE</div>'
            '<div class="disclaimer">The last forecast is retained for review and is not current live data.</div></div>',
            unsafe_allow_html=True,
        )
    if not horizons:
        st.caption("WAITING FOR LIVE HISTORY")
        return

    primary = horizons[0]
    threshold = float(forecast.get("threshold") or 0)
    _render_operational_status(
        warning=bool(primary.get("warning")),
        score=float(primary.get("score", 0.0)),
        threshold=threshold,
        context="live capture · L=10 history",
        reference_timestamp=str(forecast.get("reference_timestamp") or "Unavailable"),
    )
    _section("Forecast horizon", "+10s primary · direct K=5 outputs")
    _render_forecast_timeline(horizons, threshold)
    _section("Forecast Score Trajectory", "live score against operating threshold")
    _render_forecast_chart(horizons, threshold)
    with st.expander("Explanation"):
        st.json(forecast.get("explanation") or {})


def _render_live_sources(source_priorities: list[dict[str, object]], mitigation: dict[str, object]) -> None:
    _section("Source intelligence", "live candidate-source activity")
    _render_source_cards(source_priorities, limit=3)
    st.caption("Candidate-source priority is based on measured activity. It is not attacker attribution; no traffic is automatically blocked.")
    _section("Recommended response", "simulation only")
    st.markdown(
        '<div class="simulation-banner"><span><strong>SIMULATION ONLY: TRUE</strong> · recommendation-only response</span>'
        '<span>AUTOMATIC BLOCKING DISABLED</span></div>',
        unsafe_allow_html=True,
    )
    _render_mitigation_cards(list(mitigation.get("recommendations") or []), source_priorities)


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
    _section("Live telemetry", f"{mode} · {interface}")
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

    st.caption("Real packet capture mode. The dashboard never substitutes replay data for live telemetry.")
    _render_live_runtime()


def main() -> None:
    st.set_page_config(page_title="Sentinel / Network Intelligence", page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")
    _render_header()
    st.sidebar.markdown(
        '<div class="brand-lockup"><div class="brand-mark">WORKSPACE</div>'
        '<div class="brand-name" style="font-size:1rem">Command center</div>'
        '<div class="brand-sub">Analyst presentation surface</div></div>',
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("<div class='eyebrow'>Navigation</div>", unsafe_allow_html=True)
    mode = st.sidebar.radio(
        "Workspace",
        ["LIVE", "REPLAY", "MOCK / STATIC", "Full Integrated Demo"],
        index=3,
        label_visibility="collapsed",
    )
    st.sidebar.markdown("---")
    st.sidebar.caption("Frozen contract")
    st.sidebar.caption("10-second state cadence · L=10 · K=5")
    st.sidebar.caption("Recommendation-only response")
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
