import type { ForecastRow, SensorForecastResponse, SensorSummary } from "../lib/types";
import { ForecastView } from "./ForecastView";

type DetailView = "Forecast" | "Sources" | "Mitigation";

function freshness(value?: number | null) {
  if (typeof value !== "number") return "No receipt recorded";
  return value < 60 ? `${Math.max(0, Math.round(value))}s ago` : `${Math.round(value / 60)}m ago`;
}

function forecastRows(result: SensorForecastResponse | null): ForecastRow[] {
  return result?.forecast?.forecast || [];
}

export function SensorDetail({
  sensor,
  forecast,
  forecastError,
  onNavigate,
}: {
  sensor: SensorSummary | null;
  forecast: SensorForecastResponse | null;
  forecastError: string | null;
  onNavigate: (view: DetailView) => void;
}) {
  if (!sensor) return <section className="section-block empty-state"><span className="empty-mark">—</span><div><strong>Select a sensor to inspect.</strong><p>Open Sensors and choose a registered server.</p></div></section>;

  const isOffline = sensor.status === "OFFLINE";
  const telemetryStale = sensor.telemetry_status === "STALE" || sensor.status === "DEGRADED";
  const forecastWaiting = !forecast || !forecast.forecast_ready;
  const readyForCurrentForecast = sensor.status === "ONLINE" && sensor.telemetry_status === "FRESH" && forecast?.forecast_ready === true;
  const detailState = isOffline ? "SENSOR OFFLINE" : telemetryStale ? "TELEMETRY STALE" : forecastWaiting ? "FORECAST WAITING" : readyForCurrentForecast ? "SENSOR ONLINE" : "REGISTERED";
  const rows = readyForCurrentForecast ? forecastRows(forecast) : [];

  return <section className="section-block sensor-detail-page" aria-labelledby="sensor-detail-heading">
    <div className="section-heading"><div><p className="overline">Sensor detail</p><h2 id="sensor-detail-heading">{sensor.hostname}</h2><p className="section-description"><code>{sensor.sensor_id}</code> · status is derived from central registry, heartbeat, and telemetry receipts.</p></div><span className={`${stateClass(detailState)} detail-state`}>{detailState}</span></div>

    <div className="detail-health-grid">
      <div><span>Agent</span><strong>{sensor.agent_status || "UNKNOWN"}</strong><small>last heartbeat {freshness(sensor.heartbeat_freshness_seconds)}</small></div>
      <div><span>Telemetry</span><strong>{sensor.telemetry_status || "UNKNOWN"}</strong><small>last state {freshness(sensor.telemetry_freshness_seconds)}</small></div>
      <div><span>Forecast</span><strong>{readyForCurrentForecast ? "READY" : "WAITING"}</strong><small>{sensor.runtime?.history_length ?? 0} / {sensor.runtime?.history_required ?? 10} states</small></div>
      <div><span>Capture</span><strong>{sensor.capture_status || "UNKNOWN"}</strong><small>{sensor.connection_status || "DISCONNECTED"}</small></div>
    </div>

    {isOffline && <div className="detail-state-message detail-state-bad"><strong>Sensor offline.</strong><p>No fresh heartbeat is being received. Any retained runtime result is withheld from the current view.</p></div>}
    {!isOffline && telemetryStale && <div className="detail-state-message detail-state-warn"><strong>Telemetry stale.</strong><p>Heartbeat may still be fresh, but telemetry is not current. Forecast values are withheld until fresh telemetry returns.</p></div>}
    {!isOffline && !telemetryStale && forecastWaiting && <div className="detail-state-message"><strong>Forecast waiting.</strong><p>The sensor is registered and reporting, but the central service needs ten valid contiguous states before a forecast is available.</p></div>}
    {forecastError && <div className="detail-state-message detail-state-bad"><strong>Forecast unavailable.</strong><p>{forecastError}</p></div>}

    <div className="detail-actions" aria-label="Sensor detail views"><button className="button-quiet" onClick={() => onNavigate("Forecast")}>Forecast</button><button className="button-quiet" onClick={() => onNavigate("Sources")}>Sources</button><button className="button-quiet" onClick={() => onNavigate("Mitigation")}>Mitigation</button></div>
    <ForecastView rows={rows} threshold={readyForCurrentForecast ? forecast?.forecast?.threshold : undefined} explanation={readyForCurrentForecast ? forecast?.forecast?.explanation : undefined} status={isOffline ? "STOPPED" : telemetryStale ? "STALE_NOT_LIVE" : "BUILDING_HISTORY"} />
  </section>;
}

function stateClass(value: string) {
  return value === "SENSOR ONLINE" ? "setup-state setup-state-good" : value === "TELEMETRY STALE" || value === "DEGRADED" ? "setup-state setup-state-warn" : value === "SENSOR OFFLINE" ? "setup-state setup-state-bad" : "setup-state";
}
