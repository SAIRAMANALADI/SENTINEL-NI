"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { getLive, getReady, runDemo, startTelemetry, stopTelemetry } from "../lib/api";
import type { DemoResponse, LiveResponse } from "../lib/types";
import { ForecastView } from "./ForecastView";
import { SourceIntelligence } from "./SourceIntelligence";
import { StatusPill } from "./StatusPill";
import { SignatureHero } from "./SignatureHero";
import { ThinkingSystem } from "./ThinkingSystem";
import { GuidedEntry } from "./GuidedEntry";
import { LiveJourney } from "./LiveJourney";
import { TermHelp } from "./TermHelp";

type View = "Overview" | "Live" | "Replay" | "Forecast" | "Sources" | "Recommendations" | "System";
type RuntimeState = "INITIALIZING" | "DEMO" | "REPLAY" | "LIVE" | "BUILDING_HISTORY" | "FORECAST_READY" | "STALE" | "STOPPED" | "CAPTURE_UNAVAILABLE" | "ERROR" | "BACKEND_UNAVAILABLE";
const nav: View[] = ["Overview", "Live", "Replay", "Forecast", "Sources", "Recommendations", "System"];

const number = (value: number | undefined) => typeof value === "number" ? new Intl.NumberFormat("en-US", { notation: value > 9999 ? "compact" : "standard", maximumFractionDigits: 1 }).format(value) : "—";
const toneFor = (status: string): "live" | "ready" | "warning" | "stale" | "muted" | "error" => status === "FORECAST_READY" || status === "READY" || status === "DEMO" ? "ready" : status === "CAPTURING" || status === "LIVE_RUNNING" || status === "LIVE" ? "live" : status === "STALE" || status === "STALE_NOT_LIVE" ? "stale" : status === "ERROR" || status === "BACKEND_UNAVAILABLE" || status === "CAPTURE_UNAVAILABLE" ? "error" : "muted";

function runtimeState(live: LiveResponse | null, demo: DemoResponse | null, connectionError: string | null): RuntimeState {
  if (connectionError) return "BACKEND_UNAVAILABLE";
  if (demo) return "DEMO";
  if (!live) return "INITIALIZING";
  if (live.telemetry.mode === "replay") return "REPLAY";
  if (live.telemetry.mode !== "live") return live.telemetry.readiness_state === "FORECAST_READY" ? "FORECAST_READY" : "REPLAY";
  if (["LIVE_UNAVAILABLE", "LIVE_PERMISSION_DENIED"].includes(live.telemetry.status || "")) return "CAPTURE_UNAVAILABLE";
  if (live.telemetry.readiness_state === "ERROR") return "ERROR";
  if (live.telemetry.readiness_state === "STALE" || live.forecast.stale) return "STALE";
  if (live.telemetry.readiness_state === "FORECAST_READY" || live.forecast.horizons?.length) return "FORECAST_READY";
  if (live.telemetry.status === "LIVE_RUNNING") return "BUILDING_HISTORY";
  return "STOPPED";
}

function runtimeLabel(state: RuntimeState, hasForecast: boolean) {
  if (state === "BACKEND_UNAVAILABLE") return "BACKEND UNAVAILABLE";
  if (state === "DEMO") return "DEMO READY";
  if (state === "REPLAY") return hasForecast ? "FORECAST AVAILABLE" : "REPLAY READY";
  if (state === "FORECAST_READY") return "FORECAST AVAILABLE";
  if (state === "STALE") return "DATA STALE";
  if (state === "STOPPED") return "SYSTEM STOPPED";
  return state.replaceAll("_", " ");
}

export default function CommandCenter() {
  const [view, setView] = useState<View>("Overview");
  const [live, setLive] = useState<LiveResponse | null>(null);
  const [demo, setDemo] = useState<DemoResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [demoLoading, setDemoLoading] = useState(false);
  const [telemetryBusy, setTelemetryBusy] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [current, health] = await Promise.all([getLive(), getReady()]);
      if (!health.ready) throw new Error(`Backend is not ready (${health.service_state})`);
      setLive(current);
      setConnectionError(null);
    } catch (reason) {
      setLive(null);
      setDemo(null);
      setConnectionError(reason instanceof Error ? reason.message : "Backend unavailable");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 5000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const executeDemo = async () => {
    setDemoLoading(true);
    setActionError(null);
    try {
      setDemo(await runDemo());
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : "Demo unavailable");
    } finally {
      setDemoLoading(false);
    }
  };

  const executeTelemetry = async (action: "start" | "stop") => {
    setTelemetryBusy(true);
    setActionError(null);
    try {
      if (action === "start") await startTelemetry(); else await stopTelemetry();
      await refresh();
    } catch (reason) {
      setActionError(reason instanceof Error ? reason.message : "Live monitoring action failed");
    } finally {
      setTelemetryBusy(false);
    }
  };

  const explainSystem = () => document.getElementById("thinking-heading")?.scrollIntoView({ behavior: "smooth", block: "start" });
  const state = runtimeState(live, demo, connectionError);
  const mode = demo ? "DEMO" : live?.telemetry.mode === "live" ? "LIVE" : "REPLAY";
  const forecast = demo ? { horizons: demo.network_forecast.forecasts, threshold: demo.network_forecast.threshold, explanation: demo.network_forecast.explanation, reference_timestamp: demo.network_forecast.reference_timestamp } : live?.forecast;
  const sources = demo ? demo.source_priorities : live?.source_priorities || [];
  const recommendations = demo ? demo.mitigation_recommendations : live?.mitigation?.recommendations || [];
  const primary = forecast?.horizons?.[0];
  const backendUnavailable = state === "BACKEND_UNAVAILABLE";
  const stats = useMemo(() => demo
    ? [{ label: "Network state", value: demo.network_status, note: "prepared demonstration" }, { label: "Forecast history", value: `${demo.history_length} / 10`, note: "states used for this demo" }, { label: "Candidate sources", value: String(demo.source_priorities.length), note: "ranked evidence" }]
    : [{ label: "Packets", value: number(live?.telemetry.packet_quality?.packets_seen), note: "observed traffic" }, { label: "Flows", value: number(live?.telemetry.flow_count), note: "completed flows" }, { label: "Network states", value: number(live?.state.valid_state_count), note: "total valid states" }, { label: "Forecast history", value: `${live?.state.buffer_size ?? 0} / ${live?.state.buffer_required ?? 10}`, note: "states used for forecast" }], [demo, live]);

  return <main className="product-shell">
    <aside className="navigation"><div className="brand"><span className="brand-kicker">SIH26-26153</span><strong>SENTINEL<span>/</span>NI</strong><small>Network monitoring</small></div><nav aria-label="Primary navigation">{nav.map((item) => <button className={view === item ? "nav-item active" : "nav-item"} onClick={() => setView(item)} key={item}>{item}<span>↗</span></button>)}</nav><div className="nav-footer"><p>10-second network states</p><p>Recommendations only</p></div></aside>
    <section className="workspace">
      <header className="topbar"><div><span className="topbar-context">{view}</span><span className="topbar-title">Sentinel / Network Intelligence</span></div><div className="topbar-right"><StatusPill label={runtimeLabel(state, Boolean(primary))} tone={toneFor(state)} /><span className="topbar-mode">{mode} MODE</span></div></header>
      {actionError && !backendUnavailable && <div className="error-strip"><strong>ACTION NOT COMPLETED</strong><span>{actionError}</span><button onClick={() => setActionError(null)}>Dismiss</button></div>}
      {backendUnavailable ? <BackendUnavailable message={connectionError || "The processing service did not respond."} onRetry={() => void refresh()} /> : <>
        {view === "Overview" && <SignatureHero forecast={forecast} live={live} mode={mode} status={state} onReplay={() => void executeDemo()} onLive={() => setView("Live")} loading={demoLoading} />}
        {(view === "Overview" || view === "Live" || view === "Forecast") && <section className="hero-grid"><div className={`primary-forecast ${primary?.warning ? "is-warning" : ""}`}><div className="hero-top"><span className="overline">{demo ? "Prepared demonstration traffic" : state === "STALE" ? "Retained forecast · not current" : "Current network outlook"}</span><StatusPill label={`${mode} MODE`} tone={mode === "LIVE" ? toneFor(state) : "muted"} /></div>{primary ? <><span className="hero-status">{primary.warning ? "Predictive warning" : "No predictive warning"}</span><strong className="hero-score">{primary.score.toFixed(4)}</strong><span className="hero-score-label">Forecast Score · +10s primary horizon <TermHelp term="Forecast Score">A model score representing the strength of the forecast signal for a future network state. It is not a calibrated probability.</TermHelp></span><div className="hero-meta"><span>Threshold <b>{forecast?.threshold?.toFixed(2) ?? "—"}</b></span><span>Reference <b>{forecast?.reference_timestamp || "—"}</b></span><span>Model <b>LSTM K=5</b></span></div><p className="hero-meaning">{primary.warning ? "The +10 second forecast score meets the configured operating threshold. This does not mean an attack is confirmed." : "The +10 second forecast score is below the configured operating threshold."}</p></> : <div className="history-state"><span className="history-count">{demo?.history_length ?? live?.state.buffer_size ?? 0}<i>/</i>{demo ? 10 : live?.state.buffer_required ?? 10}</span><strong>{state === "STOPPED" || state === "REPLAY" ? "Waiting for network data" : state === "ERROR" || state === "CAPTURE_UNAVAILABLE" ? "Forecast unavailable" : "Building forecast history"}</strong><p>{state === "STOPPED" || state === "REPLAY" ? "Run the demo or start live monitoring to produce a forecast." : state === "ERROR" || state === "CAPTURE_UNAVAILABLE" ? "The capture or processing service did not provide a usable forecast." : "Collecting valid network observations. Forecast activates after 10 recent states."}</p></div>}</div><div className="context-panel"><span className="overline">System status</span><div className="context-line"><span>Mode</span><strong>{mode}</strong></div><div className="context-line"><span>Capture status</span><strong>{demo ? "PREPARED DATA" : live?.telemetry.status || "—"}</strong></div><div className="context-line"><span>Interface</span><strong>{demo ? "No live capture" : live?.telemetry.interface || "Not configured"}</strong></div><div className="context-line"><span>Freshness</span><strong>{demo ? "NOT LIVE" : live?.telemetry.freshness || "NOT CURRENT"}</strong></div><div className="context-callout"><span>Candidate sources</span><strong>{sources.length ? `${sources.length} to review` : "No source activity"}</strong><small>Ranked evidence, not attribution.</small></div></div></section>}
        {(view === "Overview" || view === "Live") && <section className="stats-block"><div className="section-heading"><div><p className="overline">Network activity</p><h2>Current network state</h2></div><span className="section-note">{demo ? "prepared demonstration traffic" : live?.telemetry.last_event_at ? `last event ${live.telemetry.last_event_at}` : "waiting for telemetry"}</span></div><div className="stat-row">{stats.map((item) => <div className="stat" key={item.label}><span>{item.label}</span><strong>{item.value}</strong><small>{item.note}</small></div>)}</div></section>}
        {view === "Overview" && <GuidedEntry onReplay={() => void executeDemo()} onLive={() => setView("Live")} onHow={explainSystem} loading={demoLoading} />}
        {view === "Live" && <LiveJourney live={live} onStart={() => void executeTelemetry("start")} onStop={() => void executeTelemetry("stop")} busy={telemetryBusy} />}
        {view === "Replay" && <ReplayPanel demo={demo} loading={demoLoading} onDemo={() => void executeDemo()} />}
        {(view === "Overview" || view === "Forecast") && <ForecastView rows={forecast?.horizons || []} threshold={forecast?.threshold} explanation={forecast?.explanation} status={forecast?.stale ? "STALE_NOT_LIVE" : state} />}
        {(view === "Overview" || view === "Sources") && <SourceIntelligence sources={sources} recommendations={recommendations} />}
        {view === "Overview" && <ThinkingSystem />}
        {view === "Recommendations" && <Operations mode={mode} live={live} onDemo={() => void executeDemo()} loading={demoLoading} />}
        {view === "System" && <SystemPanel live={live} loading={loading} state={state} />}
        {view === "Overview" && <footer className="disclaimer-footer">Forecast Score is not a calibrated probability · Candidate sources are not confirmed attribution · Simulation only: TRUE</footer>}
      </>}
    </section>
  </main>;
}

function BackendUnavailable({ message, onRetry }: { message: string; onRetry: () => void }) {
  return <section className="backend-outage section-block" aria-labelledby="backend-outage-heading"><div className="backend-outage-mark">!</div><div><p className="overline">Runtime state</p><h1 id="backend-outage-heading">BACKEND UNAVAILABLE</h1><p>Sentinel cannot reach the processing service.</p><small>{message}</small><button onClick={onRetry}>Retry connection</button></div></section>;
}

function Operations({ mode, live, onDemo, loading }: { mode: string; live: LiveResponse | null; onDemo: () => void; loading: boolean }) {
  return <section className="section-block operations"><div className="section-heading"><div><p className="overline">Recommendations</p><h2>Review the next action</h2></div></div><div className="operation-grid"><div className="operation-card"><span className="overline">Current mode</span><strong>{mode}</strong><p>{live?.telemetry.mode === "live" ? "Network traffic is being observed through the configured interface." : "Prepared data is clearly identified as demo mode."}</p></div><div className="operation-card"><span className="overline">Demo</span><strong>Prepared demonstration traffic</strong><p>Review the complete forecast, source ranking, and recommendation path.</p><button onClick={onDemo} disabled={loading}>{loading ? "Running…" : "Run demo"}</button></div></div></section>;
}

function SystemPanel({ live, loading, state }: { live: LiveResponse | null; loading: boolean; state: RuntimeState }) {
  return <section className="section-block operations"><div className="section-heading"><div><p className="overline">System</p><h2>Runtime status</h2></div><span className="section-note">updated every 5 seconds</span></div><div className="system-grid"><div className="system-card"><StatusPill label={loading ? "CONNECTING" : live ? runtimeLabel(state, Boolean(live.forecast.horizons?.length)) : "BACKEND UNAVAILABLE"} tone={loading ? "muted" : live ? toneFor(state) : "error"} /><p>Runtime state is authoritative for telemetry, history, forecast freshness, source ranking, and recommendations.</p></div><div className="system-card"><span className="overline">Configuration</span><p>10-second state cadence<br />10-state forecast history · 5 forecast points<br />Recommendations only<br />No payloads retained in the frontend</p></div></div><details className="technical-details"><summary>View technical details</summary><p>Frontend state is derived from the readiness and live contracts. A failed health/live request suppresses current result data. Demo output is a separate prepared-data session and is never combined with live telemetry.</p></details></section>;
}

function ReplayPanel({ demo, loading, onDemo }: { demo: DemoResponse | null; loading: boolean; onDemo: () => void }) {
  return <section className="section-block replay-panel"><div className="replay-hero"><div><StatusPill label="DEMO MODE" tone="muted" /><h2>See the complete system with prepared traffic.</h2><p>The demo shows the forecast, candidate sources, recommendations, and explanation path. It is not live network telemetry.</p></div><button onClick={onDemo} disabled={loading}>{loading ? "Running…" : "Run demo"}</button></div>{demo && <><ForecastView rows={demo.network_forecast.forecasts} threshold={demo.network_forecast.threshold} explanation={demo.network_forecast.explanation} status="DEMO" /><SourceIntelligence sources={demo.source_priorities} recommendations={demo.mitigation_recommendations} /></>}</section>;
}
