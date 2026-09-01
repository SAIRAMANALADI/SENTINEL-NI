import type { SensorSummary } from "../lib/types";

function freshness(value?: number | null) {
  if (typeof value !== "number") return "—";
  if (value < 60) return `${Math.round(value)}s ago`;
  return `${Math.round(value / 60)}m ago`;
}

export function SensorFleet({ sensors }: { sensors: SensorSummary[] }) {
  return <section className="section-block sensor-fleet" aria-labelledby="sensor-fleet-heading">
    <div className="section-heading">
      <div><p className="overline">Infrastructure</p><h2 id="sensor-fleet-heading">Connected servers</h2><p className="section-description">Remote sensors send aggregated network states to this processing service. The central server does not capture their packets directly.</p></div>
      <span className="section-note">{sensors.length} registered sensor{sensors.length === 1 ? "" : "s"}</span>
    </div>
    {sensors.length === 0 ? <div className="empty-state"><span className="empty-mark">—</span><div><strong>No remote sensors registered</strong><p>Create an enrollment credential, then register a Sentinel agent on the connected server.</p></div></div> : <div className="sensor-list">{sensors.map((sensor) => <article className={`sensor-card sensor-${sensor.status.toLowerCase()}`} key={sensor.sensor_id}><div className="sensor-card-top"><div><span className="sensor-status">{sensor.status}</span><h3>{sensor.hostname}</h3><code>{sensor.sensor_id}</code></div><span className="sensor-agent">AGENT {sensor.agent_version}</span></div><div className="sensor-facts"><span><small>Last heartbeat</small><strong>{freshness(sensor.heartbeat_freshness_seconds)}</strong></span><span><small>Last telemetry</small><strong>{freshness(sensor.telemetry_freshness_seconds)}</strong></span><span><small>States</small><strong>{sensor.runtime?.state_count ?? 0}</strong></span><span><small>History</small><strong>{sensor.runtime?.history_length ?? 0} / {sensor.runtime?.history_required ?? 10}</strong></span></div><details className="technical-details"><summary>Technical details</summary><p>Sequence {sensor.last_sequence ?? 0} · buffered batches {sensor.buffered_item_count ?? 0} · forecast {sensor.runtime?.forecast_status ?? "BUILDING_HISTORY"}.</p></details></article>)}</div>}
  </section>;
}
