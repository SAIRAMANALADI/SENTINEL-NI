"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { DashboardUnauthorizedError, getLive, getReady, getSensor, getSensorForecast, getSensors, runDemo, startTelemetry, stopTelemetry } from "../lib/api";
import type { DemoResponse, FleetHealth, LiveResponse, SensorForecastResponse, SensorSummary } from "../lib/types";
import { ForecastView } from "./ForecastView";
import { SourceIntelligence } from "./SourceIntelligence";
import { StatusPill } from "./StatusPill";
import { SignatureHero } from "./SignatureHero";
import { ThinkingSystem } from "./ThinkingSystem";
import { GuidedEntry } from "./GuidedEntry";
import { LiveJourney } from "./LiveJourney";
import { TermHelp } from "./TermHelp";
import { SensorFleet } from "./SensorFleet";
import { SensorOnboarding } from "./SensorOnboarding";
import { SensorDetail } from "./SensorDetail";

type View = "Overview" | "Live" | "Replay" | "Forecast" | "Sources" | "Sensors" | "Add Sensor" | "Sensor Detail" | "Mitigation" | "System";
type RuntimeState = "INITIALIZING" | "DEMO" | "MOCK" | "REPLAY" | "LIVE" | "BUILDING_HISTORY" | "FORECAST_READY" | "STALE" | "STOPPED" | "CAPTURE_UNAVAILABLE" | "ERROR" | "BACKEND_UNAVAILABLE" | "BACKEND_DEGRADED" | "SENSOR_OFFLINE" | "TELEMETRY_STALE" | "FORECAST_WAITING" | "SENSOR_ONLINE";
const nav: View[] = ["Overview", "Live", "Sensors", "Add Sensor", "Forecast", "Sources", "Mitigation", "Replay", "System"];

const number = (value: number | undefined) => typeof value === "number" ? new Intl.NumberFormat("en-US", { notation: value > 9999 ? "compact" : "standard", maximumFractionDigits: 1 }).format(value) : "—";
const freshnessLabel = (value: number | null | undefined) => typeof value === "number" ? `${Math.max(0, Math.round(value))}s ago` : "NOT RECEIVING";
const toneFor = (status: string): "live" | "ready" | "warning" | "stale" | "muted" | "error" => status === "FORECAST_READY" || status === "READY" || status === "DEMO" || status === "SENSOR_ONLINE" ? "ready" : status === "CAPTURING" || status === "LIVE_RUNNING" || status === "LIVE" ? "live" : status === "STALE" || status === "STALE_NOT_LIVE" || status === "TELEMETRY_STALE" ? "stale" : status === "ERROR" || status === "BACKEND_UNAVAILABLE" || status === "CAPTURE_UNAVAILABLE" || status === "SENSOR_OFFLINE" ? "error" : status === "FORECAST_WAITING" || status === "BACKEND_DEGRADED" ? "warning" : "muted";

function runtimeState(live: LiveResponse | null, demo: DemoResponse | null, connectionError: string | null, readinessError: string | null): RuntimeState {
  if (connectionError) return "BACKEND_UNAVAILABLE";
  if (readinessError) return "BACKEND_DEGRADED";
  if (demo) return "DEMO";
  if (!live) return "INITIALIZING";
  if (live.telemetry.mode === "mock") return "MOCK";
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
  if (state === "BACKEND_DEGRADED") return "CENTRAL NOT READY";
  if (state === "DEMO") return "DEMO READY";
  if (state === "MOCK") return "MOCK DATA";
  if (state === "REPLAY") return hasForecast ? "FORECAST AVAILABLE" : "REPLAY READY";
  if (state === "FORECAST_READY") return "FORECAST AVAILABLE";
  if (state === "STALE") return "DATA STALE";
  if (state === "STOPPED") return "SYSTEM STOPPED";
  if (state === "SENSOR_OFFLINE") return "SENSOR OFFLINE";
  if (state === "TELEMETRY_STALE") return "TELEMETRY STALE";
  if (state === "FORECAST_WAITING") return "FORECAST WAITING";
  if (state === "SENSOR_ONLINE") return "SENSOR ONLINE";
  return state.replaceAll("_", " ");
}

function sensorRuntimeState(sensor: SensorSummary | null, forecast: SensorForecastResponse | null): RuntimeState {
  if (!sensor) return "INITIALIZING";
  if (sensor.status === "OFFLINE") return "SENSOR_OFFLINE";
  if (sensor.telemetry_status === "STALE" || sensor.status === "DEGRADED") return "TELEMETRY_STALE";
  if (sensor.status === "ONLINE" && sensor.telemetry_status === "FRESH" && forecast?.forecast_ready) return "SENSOR_ONLINE";
  return "FORECAST_WAITING";
}

export default function CommandCenter({ onLogout, onUnauthorized, role = "development" }: { onLogout?: () => void; onUnauthorized?: () => void; role?: "viewer" | "operator" | "admin" | "development" }) {
  const canOperate = role !== "viewer";
  const [view, setView] = useState<View>("Overview");
  const [live, setLive] = useState<LiveResponse | null>(null);
  const [demo, setDemo] = useState<DemoResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [demoLoading, setDemoLoading] = useState(false);
  const [telemetryBusy, setTelemetryBusy] = useState(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [readinessError, setReadinessError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [sensors, setSensors] = useState<SensorSummary[]>([]);
  const [fleetHealth, setFleetHealth] = useState<FleetHealth | null>(null);
  const [sensorError, setSensorError] = useState<string | null>(null);
  const [selectedSensorId, setSelectedSensorId] = useState<string | null>(null);
  const [selectedSensorDetail, setSelectedSensorDetail] = useState<SensorSummary | null>(null);
  const [selectedSensorForecast, setSelectedSensorForecast] = useState<SensorForecastResponse | null>(null);
  const [forecastError, setForecastError] = useState<string | null>(null);
  const [serverUrl, setServerUrl] = useState("");
  const [interfaceName, setInterfaceName] = useState("Ethernet");

  const refresh = useCallback(async () => {
    try {
      const [current, health] = await Promise.all([getLive(), getReady()]);
      setLive(current);
      setConnectionError(null);
      setReadinessError(health.ready ? null : `Central service is reachable but not ready (${health.service_state})`);
      try { const fleet = await getSensors(); setSensors(fleet.sensors); setFleetHealth(fleet.health || null); setSensorError(null); } catch (reason) { if (reason instanceof DashboardUnauthorizedError) onUnauthorized?.(); else setSensorError(reason instanceof Error ? reason.message : "Sensor fleet unavailable"); }
    } catch (reason) {
      if (reason instanceof DashboardUnauthorizedError) { onUnauthorized?.(); return; }
      setLive(null);
      setDemo(null);
      setReadinessError(null);
      setConnectionError(reason instanceof Error ? reason.message : "Backend unavailable");
    } finally {
      setLoading(false);
    }
  }, [onUnauthorized]);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 5000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  useEffect(() => {
    if (!selectedSensorId) {
      setSelectedSensorDetail(null);
      setSelectedSensorForecast(null);
      setForecastError(null);
      return;
    }
    setSelectedSensorDetail(null);
    setSelectedSensorForecast(null);
    setForecastError(null);
    let cancelled = false;
    const loadSelected = async () => {
      try {
        const detail = await getSensor(selectedSensorId);
        if (!cancelled) setSelectedSensorDetail(detail);
      } catch (reason) {
        if (reason instanceof DashboardUnauthorizedError) onUnauthorized?.();
        if (!cancelled) setSelectedSensorDetail(null);
      }
      try {
        const result = await getSensorForecast(selectedSensorId);
        if (!cancelled) { setSelectedSensorForecast(result); setForecastError(null); }
      } catch (reason) {
        if (reason instanceof DashboardUnauthorizedError) onUnauthorized?.();
        if (!cancelled) { setSelectedSensorForecast(null); setForecastError(reason instanceof Error ? reason.message : "Forecast unavailable"); }
      }
    };
    void loadSelected();
    const timer = window.setInterval(() => void loadSelected(), 5000);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, [onUnauthorized, selectedSensorId]);

  const executeDemo = async () => {
    setDemoLoading(true);
    setActionError(null);
    try {
      setDemo(await runDemo());
    } catch (reason) {
      if (reason instanceof DashboardUnauthorizedError) onUnauthorized?.();
      else setActionError(reason instanceof Error ? reason.message : "Demo unavailable");
    } finally {
      setDemoLoading(false);
    }
  };

  const executeTelemetry = async (action: "start" | "stop") => {
    setTelemetryBusy(true);
    setActionError(null);
    try {
      if (action === "start") { await startTelemetry(); setDemo(null); } else await stopTelemetry();
      await refresh();
    } catch (reason) {
      if (reason instanceof DashboardUnauthorizedError) onUnauthorized?.();
      else setActionError(reason instanceof Error ? reason.message : "Live monitoring action failed");
    } finally {
      setTelemetryBusy(false);
    }
  };

  const explainSystem = () => document.getElementById("thinking-heading")?.scrollIntoView({ behavior: "smooth", block: "start" });
  const state = runtimeState(live, demo, connectionError, readinessError);
  const selectedSensor = selectedSensorDetail || sensors.find((sensor) => sensor.sensor_id === selectedSensorId) || null;
  const selectedSensorState = sensorRuntimeState(selectedSensor, selectedSensorForecast);
  const mode = selectedSensor ? "REMOTE SENSOR" : demo ? "DEMO" : live?.telemetry.mode === "live" ? "LIVE" : live?.telemetry.mode === "mock" ? "MOCK" : "REPLAY";
  const remoteForecastReady = selectedSensorState === "SENSOR_ONLINE" && selectedSensorForecast?.forecast_ready;
  const forecast = selectedSensor ? remoteForecastReady ? { horizons: selectedSensorForecast?.forecast?.forecast || [], threshold: selectedSensorForecast?.forecast?.threshold, explanation: selectedSensorForecast?.forecast?.explanation, reference_timestamp: selectedSensorForecast?.forecast?.reference_timestamp } : undefined : demo ? { horizons: demo.network_forecast.forecasts, threshold: demo.network_forecast.threshold, explanation: demo.network_forecast.explanation, reference_timestamp: demo.network_forecast.reference_timestamp } : live?.forecast;
  const sourceDataFresh = selectedSensor?.runtime?.source_status === "SOURCE_ATTRIBUTION_AVAILABLE";
  const sources = selectedSensor ? remoteForecastReady && sourceDataFresh ? selectedSensor.runtime?.source_priorities || [] : [] : demo ? demo.source_priorities : live?.source_priorities || [];
  const recommendations = selectedSensor ? remoteForecastReady && sourceDataFresh ? selectedSensor.runtime?.mitigation?.recommendations || [] : [] : demo ? demo.mitigation_recommendations : live?.mitigation?.recommendations || [];
  const primary = forecast?.horizons?.[0];
  const displayState: RuntimeState = selectedSensor ? selectedSensorState : state;
  const backendUnavailable = state === "BACKEND_UNAVAILABLE";
  const stats = useMemo(() => selectedSensor
    ? [{ label: "Sensor status", value: selectedSensor.status, note: "registered remote server" }, { label: "Network states", value: number(selectedSensor.runtime?.state_count), note: "received from sensor" }, { label: "Forecast history", value: `${selectedSensor.runtime?.history_length ?? 0} / 10`, note: "states used for forecast" }]
    : demo
    ? [{ label: "Network state", value: demo.network_status, note: "prepared demonstration" }, { label: "Forecast history", value: `${demo.history_length} / 10`, note: "states used for this demo" }, { label: "Candidate sources", value: String(demo.source_priorities.length), note: "ranked evidence" }]
    : [{ label: "Packets", value: number(live?.telemetry.packet_quality?.packets_seen), note: "observed traffic" }, { label: "Flows", value: number(live?.telemetry.flow_count), note: "completed flows" }, { label: "Network states", value: number(live?.state.valid_state_count), note: "total valid states" }, { label: "Forecast history", value: `${live?.state.buffer_size ?? 0} / ${live?.state.buffer_required ?? 10}`, note: "states used for forecast" }], [demo, live, selectedSensor]);

  const calculatedFleetHealth: FleetHealth = fleetHealth || {
    sensor_count: sensors.length,
    online_sensor_count: sensors.filter((sensor) => sensor.status === "ONLINE").length,
    degraded_sensor_count: sensors.filter((sensor) => sensor.status === "DEGRADED").length,
    offline_sensor_count: sensors.filter((sensor) => sensor.status === "OFFLINE").length,
    active_warning_count: sensors.filter((sensor) => sensor.latest_warning && sensor.status === "ONLINE").length,
    forecast_waiting_count: sensors.filter((sensor) => !sensor.forecast_ready).length,
  };

  const openSensorDetail = () => { if (selectedSensorId) setView("Sensor Detail"); };
  const selectSensor = (sensorId: string | null) => { setSelectedSensorId(sensorId); if (sensorId) setView("Sensors"); };

  return <main className="product-shell">
    <aside className="navigation"><div className="brand"><span className="brand-kicker">SIH26-26153</span><strong>SENTINEL<span>/</span>NI</strong><small>Network monitoring</small></div><nav aria-label="Primary navigation">{nav.map((item) => <button className={view === item ? "nav-item active" : "nav-item"} onClick={() => setView(item)} key={item}>{item}<span>↗</span></button>)}</nav><div className="nav-footer"><p>10-second network states</p><p>Recommendations only</p></div></aside>
    <section className="workspace">
      <header className="topbar"><div><span className="topbar-context">{view}</span><span className="topbar-title">Sentinel / Network Intelligence</span>{selectedSensor && <span className="sensor-context">SENSOR · {selectedSensor.hostname}</span>}</div><div className="topbar-right"><StatusPill label={runtimeLabel(displayState, Boolean(primary))} tone={toneFor(displayState)} /><span className="topbar-mode">{mode} MODE</span>{onLogout && <button className="sign-out" onClick={onLogout}>Sign out</button>}</div></header>
      {actionError && !backendUnavailable && <div className="error-strip"><strong>ACTION NOT COMPLETED</strong><span>{actionError}</span><button onClick={() => setActionError(null)}>Dismiss</button></div>}
      {selectedSensor && <div className="selected-sensor-banner"><span className="overline">Selected sensor</span><strong>{selectedSensor.hostname}</strong><code>{selectedSensor.sensor_id}</code><span>{selectedSensor.status} · {selectedSensor.telemetry_status || "UNKNOWN"} TELEMETRY</span></div>}
      {backendUnavailable ? <BackendUnavailable message={connectionError || "The processing service did not respond."} onRetry={() => void refresh()} /> : <>
        {readinessError && <div className="warning-strip"><strong>CENTRAL SERVICE NOT READY</strong><span>{readinessError}</span><button onClick={() => void refresh()}>Retry readiness</button></div>}
        {view === "Overview" && <SignatureHero forecast={forecast} live={live} mode={mode} status={state} onAddSensor={() => setView("Add Sensor")} onSensors={() => setView("Sensors")} onReplay={() => void executeDemo()} loading={demoLoading} canOperate={canOperate} />}
        {view === "Overview" && sensors.length > 0 && <FleetOverview health={calculatedFleetHealth} />}
        {(view === "Overview" || view === "Live" || view === "Forecast") && <section className="hero-grid"><div className={`primary-forecast ${primary?.warning ? "is-warning" : ""}`}><div className="hero-top"><span className="overline">{demo ? "Prepared demonstration traffic" : displayState === "STALE" ? "Retained forecast · not current" : "Current network outlook"}</span><StatusPill label={`${mode} MODE`} tone={mode === "LIVE" ? toneFor(state) : "muted"} /></div>{primary ? <><span className="hero-status">{primary.warning ? "Predictive warning" : "No predictive warning"}</span><strong className="hero-score">{primary.score.toFixed(4)}</strong><span className="hero-score-label">Forecast Score · +10s primary horizon <TermHelp term="Forecast Score">A model score representing the strength of the forecast signal for a future network state. It is not a calibrated probability.</TermHelp></span><div className="hero-meta"><span>Threshold <b>{forecast?.threshold?.toFixed(2) ?? "—"}</b></span><span>Reference <b>{forecast?.reference_timestamp || "—"}</b></span><span>Model <b>LSTM K=5</b></span></div><p className="hero-meaning">{primary.warning ? "The +10 second forecast score meets the configured operating threshold. This does not mean an attack is confirmed." : "The +10 second forecast score is below the configured operating threshold."}</p></> : <div className="history-state"><span className="history-count">{selectedSensor?.runtime?.history_length ?? demo?.history_length ?? live?.state.buffer_size ?? 0}<i>/</i>{selectedSensor ? 10 : demo ? 10 : live?.state.buffer_required ?? 10}</span><strong>{displayState === "STOPPED" || displayState === "REPLAY" ? "Waiting for network data" : displayState === "ERROR" || displayState === "CAPTURE_UNAVAILABLE" ? "Forecast unavailable" : "Building forecast history"}</strong><p>{displayState === "STOPPED" || displayState === "REPLAY" ? "Run the demo or start live monitoring to produce a forecast." : displayState === "ERROR" || displayState === "CAPTURE_UNAVAILABLE" ? "The capture or processing service did not provide a usable forecast." : "Collecting valid network observations. Forecast activates after 10 recent states."}</p></div>}</div><div className="context-panel"><span className="overline">System status</span><div className="context-line"><span>Mode</span><strong>{mode}</strong></div><div className="context-line"><span>Capture status</span><strong>{selectedSensor ? selectedSensor.status : demo ? "PREPARED DATA" : live?.telemetry.status || "—"}</strong></div><div className="context-line"><span>Interface</span><strong>{selectedSensor ? "Agent-side capture" : demo ? "No live capture" : live?.telemetry.interface || "Not configured"}</strong></div><div className="context-line"><span>Freshness</span><strong>{selectedSensor ? freshnessLabel(selectedSensor.telemetry_freshness_seconds) : demo ? "NOT LIVE" : live?.telemetry.freshness || "NOT CURRENT"}</strong></div><div className="context-callout"><span>Candidate sources</span><strong>{sources.length ? `${sources.length} to review` : "No source activity"}</strong><small>Ranked evidence, not attribution.</small></div></div></section>}
        {(view === "Overview" || view === "Live") && <section className="stats-block"><div className="section-heading"><div><p className="overline">Network activity</p><h2>Current network state</h2></div><span className="section-note">{selectedSensor ? `telemetry from ${selectedSensor.hostname}` : demo ? "prepared demonstration traffic" : live?.telemetry.last_event_at ? `last event ${live.telemetry.last_event_at}` : "waiting for telemetry"}</span></div><div className="stat-row">{stats.map((item) => <div className="stat" key={item.label}><span>{item.label}</span><strong>{item.value}</strong><small>{item.note}</small></div>)}</div></section>}
        {view === "Overview" && <GuidedEntry onReplay={() => void executeDemo()} onHow={explainSystem} onAddSensor={() => setView("Add Sensor")} onSensors={() => setView("Sensors")} loading={demoLoading} canOperate={canOperate} />}
        {view === "Live" && <LiveJourney live={live} onStart={() => void executeTelemetry("start")} onStop={() => void executeTelemetry("stop")} busy={telemetryBusy} canOperate={canOperate} />}
        {view === "Replay" && <ReplayPanel demo={demo} loading={demoLoading} onDemo={() => void executeDemo()} canOperate={canOperate} />}
        {(view === "Overview" || view === "Forecast") && <ForecastView rows={forecast?.horizons || []} threshold={forecast?.threshold} explanation={forecast?.explanation} status={forecast?.stale ? "STALE_NOT_LIVE" : state} />}
        {(view === "Overview" || view === "Sources") && <SourceIntelligence sources={sources} recommendations={recommendations} sensorId={selectedSensor?.sensor_id} />}
        {view === "Overview" && <ThinkingSystem />}
        {view === "System" && <SystemPanel live={live} loading={loading} state={state} />}
        {view === "Sensors" && <SensorFleet sensors={sensors} error={sensorError} selectedSensorId={selectedSensorId} onSelect={selectSensor} onAddSensor={() => setView("Add Sensor")} onOpenDetail={openSensorDetail} />}
        {view === "Add Sensor" && <SensorOnboarding sensors={sensors} selectedSensor={selectedSensor} onSelectSensor={(sensorId) => setSelectedSensorId(sensorId)} onOpenSensor={openSensorDetail} serverUrl={serverUrl} interfaceName={interfaceName} onServerUrlChange={setServerUrl} onInterfaceChange={setInterfaceName} />}
        {view === "Sensor Detail" && <SensorDetail sensor={selectedSensor} forecast={selectedSensorForecast} forecastError={forecastError} onNavigate={setView} />}
        {view === "Mitigation" && <SourceIntelligence sources={sources} recommendations={recommendations} sensorId={selectedSensor?.sensor_id} />}
        {view === "Overview" && <footer className="disclaimer-footer">Forecast Score is not a calibrated probability · Candidate sources are not confirmed attribution · Simulation only: TRUE</footer>}
      </>}
    </section>
  </main>;
}

function BackendUnavailable({ message, onRetry }: { message: string; onRetry: () => void }) {
  return <section className="backend-outage section-block" aria-labelledby="backend-outage-heading"><div className="backend-outage-mark">!</div><div><p className="overline">Runtime state</p><h1 id="backend-outage-heading">BACKEND UNAVAILABLE</h1><p>Sentinel cannot reach the processing service.</p><small>{message}</small><button onClick={onRetry}>Retry connection</button></div></section>;
}

function FleetOverview({ health }: { health: FleetHealth }) {
  const items = [
    ["Total sensors", health.sensor_count, "registered fleet"],
    ["Online", health.online_sensor_count, "fresh agent + telemetry"],
    ["Degraded", health.degraded_sensor_count, "attention required"],
    ["Offline", health.offline_sensor_count, "no fresh heartbeat"],
    ["Predictive warnings", health.active_warning_count, "current online sensors"],
    ["Forecast waiting", health.forecast_waiting_count, "building L=10 history"],
  ];
  return <section className="fleet-overview section-block" aria-labelledby="fleet-overview-heading"><div className="section-heading"><div><p className="overline">Fleet overview</p><h2 id="fleet-overview-heading">What is happening across the fleet?</h2></div><span className="section-note">live central counts</span></div><div className="fleet-metrics">{items.map(([label, value, note]) => <div className="fleet-metric" key={String(label)}><span>{label}</span><strong>{value}</strong><small>{note}</small></div>)}</div></section>;
}

function Operations({ mode, live, onDemo, loading }: { mode: string; live: LiveResponse | null; onDemo: () => void; loading: boolean }) {
  return <section className="section-block operations"><div className="section-heading"><div><p className="overline">Recommendations</p><h2>Review the next action</h2></div></div><div className="operation-grid"><div className="operation-card"><span className="overline">Current mode</span><strong>{mode}</strong><p>{live?.telemetry.mode === "live" ? "Network traffic is being observed through the configured interface." : live?.telemetry.mode === "mock" ? "Mock/static telemetry is clearly identified and is not live capture." : "Prepared data is clearly identified as replay/demo mode."}</p></div><div className="operation-card"><span className="overline">Demo</span><strong>Prepared demonstration traffic</strong><p>Review the complete forecast, source ranking, and recommendation path.</p><button onClick={onDemo} disabled={loading}>{loading ? "Running…" : "Run demo"}</button></div></div></section>;
}

function SystemPanel({ live, loading, state }: { live: LiveResponse | null; loading: boolean; state: RuntimeState }) {
  return <section className="section-block operations"><div className="section-heading"><div><p className="overline">System</p><h2>Runtime status</h2></div><span className="section-note">updated every 5 seconds</span></div><div className="system-grid"><div className="system-card"><StatusPill label={loading ? "CONNECTING" : live ? runtimeLabel(state, Boolean(live.forecast.horizons?.length)) : "BACKEND UNAVAILABLE"} tone={loading ? "muted" : live ? toneFor(state) : "error"} /><p>Runtime state is authoritative for telemetry, history, forecast freshness, source ranking, and recommendations.</p></div><div className="system-card"><span className="overline">Configuration</span><p>10-second state cadence<br />10-state forecast history · 5 forecast points<br />Recommendations only<br />No payloads retained in the frontend</p></div></div><details className="technical-details"><summary>View technical details</summary><p>Frontend state is derived from the readiness and live contracts. A failed health/live request suppresses current result data. Demo output is a separate prepared-data session and is never combined with live telemetry.</p></details></section>;
}

function ReplayPanel({ demo, loading, onDemo, canOperate }: { demo: DemoResponse | null; loading: boolean; onDemo: () => void; canOperate: boolean }) {
  return <section className="section-block replay-panel"><div className="replay-hero"><div><StatusPill label="DEMO MODE" tone="muted" /><h2>See the complete system with prepared traffic.</h2><p>The demo shows the forecast, candidate sources, recommendations, and explanation path. It is not live network telemetry.</p></div>{canOperate && <button onClick={onDemo} disabled={loading}>{loading ? "Running…" : "Run demo"}</button>}</div>{demo && <><ForecastView rows={demo.network_forecast.forecasts} threshold={demo.network_forecast.threshold} explanation={demo.network_forecast.explanation} status="DEMO" /><SourceIntelligence sources={demo.source_priorities} recommendations={demo.mitigation_recommendations} /></>}</section>;
}
