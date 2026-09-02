import { useState } from "react";
import type { SensorSummary } from "../lib/types";

function freshness(value?: number | null) {
  if (typeof value !== "number") return "—";
  if (value < 60) return `${Math.round(value)}s ago`;
  return `${Math.round(value / 60)}m ago`;
}

export function SensorFleet({ sensors, selectedSensorId, onSelect }: { sensors: SensorSummary[]; selectedSensorId: string | null; onSelect: (sensorId: string | null) => void }) {
  const [serverUrl, setServerUrl] = useState(() => typeof window === "undefined" ? "" : window.location.origin);
  const [interfaceName, setInterfaceName] = useState("Ethernet");
  const commands = [
    `python -m src.agent init --server-url ${serverUrl} --interface "${interfaceName}"`,
    "python -m src.agent register --enrollment-token <one-time-enrollment-token>",
    "python -m src.agent start",
  ].join("\n");

  return <section className="section-block sensor-fleet" aria-labelledby="sensor-fleet-heading">
    <div className="section-heading"><div><p className="overline">Infrastructure</p><h2 id="sensor-fleet-heading">Connected servers</h2><p className="section-description">Remote sensors send aggregated network states to this processing service. The central server does not capture their packets directly.</p></div><span className="section-note">{sensors.length} registered sensor{sensors.length === 1 ? "" : "s"}</span></div>
    <div className="connect-server"><div><p className="overline">Onboarding</p><h3>Add a remote server</h3><p>Enrollment is controlled through the central administrator path. The browser never receives or sends a global admin credential. The remote operator runs the agent; customer requests remain outside Sentinel.</p></div><div className="connect-fields"><label>Central URL<input value={serverUrl} onChange={(event) => setServerUrl(event.target.value)} /></label><label>Interface<input value={interfaceName} onChange={(event) => setInterfaceName(event.target.value)} /></label></div><div className="enrollment-result"><strong>Five-step connection</strong><small>1. An administrator creates a one-time enrollment credential on the central server. 2. Install the agent on the remote host. 3. Register it once. 4. Start the agent and wait for a heartbeat. 5. The sensor becomes ONLINE only after fresh heartbeat and telemetry.</small><pre>{commands}</pre></div></div>
    {sensors.length === 0 ? <div className="empty-state"><span className="empty-mark">—</span><div><strong>No remote sensors registered</strong><p>Use the central administrator path to create an enrollment credential, then register a Sentinel agent on the connected server.</p></div></div> : <div className="sensor-list">{sensors.map((sensor) => <article className={`sensor-card sensor-${sensor.status.toLowerCase()} ${selectedSensorId === sensor.sensor_id ? "sensor-selected" : ""}`} key={sensor.sensor_id}><button className="sensor-select" onClick={() => onSelect(selectedSensorId === sensor.sensor_id ? null : sensor.sensor_id)} aria-pressed={selectedSensorId === sensor.sensor_id}><div className="sensor-card-top"><div><span className="sensor-status">{sensor.status}</span><h3>{sensor.hostname}</h3><code>{sensor.sensor_id}</code></div><span className="sensor-agent">AGENT {sensor.agent_version}</span></div><div className="sensor-facts"><span><small>Last heartbeat</small><strong>{freshness(sensor.heartbeat_freshness_seconds)}</strong></span><span><small>Last telemetry</small><strong>{freshness(sensor.telemetry_freshness_seconds)}</strong></span><span><small>States</small><strong>{sensor.runtime?.state_count ?? 0}</strong></span><span><small>History</small><strong>{sensor.runtime?.history_length ?? 0} / {sensor.runtime?.history_required ?? 10}</strong></span></div></button>{selectedSensorId === sensor.sensor_id && <div className="sensor-detail"><p><strong>Selected server</strong> · all forecast context below is scoped to this sensor.</p><p>Forecast: {sensor.runtime?.forecast_status ?? "BUILDING_HISTORY"} · Candidate Sources: {sensor.runtime?.source_status === "UNAVAILABLE_FROM_AGGREGATED_STATE_TELEMETRY" ? "not available from state-only telemetry" : "available"}.</p></div>}<details className="technical-details"><summary>Technical details</summary><p>Sequence {sensor.last_sequence ?? 0} · buffered batches {sensor.buffered_item_count ?? 0} · forecast {sensor.runtime?.forecast_status ?? "BUILDING_HISTORY"}.</p></details></article>)}</div>}
  </section>;
}
