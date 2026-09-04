import type { SensorSummary } from "../lib/types";

function freshness(value?: number | null) {
  if (typeof value !== "number") return "—";
  if (value < 60) return `${Math.max(0, Math.round(value))}s ago`;
  return `${Math.round(value / 60)}m ago`;
}

function healthValue(sensor: SensorSummary, plane: "agent" | "telemetry" | "forecast") {
  if (plane === "agent") return sensor.health?.agent || sensor.agent_status || "UNKNOWN";
  if (plane === "telemetry") return sensor.health?.telemetry || sensor.telemetry_status || "UNKNOWN";
  return sensor.health?.forecast || (sensor.forecast_ready ? "READY" : "WAITING");
}

export function SensorFleet({
  sensors,
  error,
  selectedSensorId,
  onSelect,
  onAddSensor,
  onOpenDetail,
}: {
  sensors: SensorSummary[];
  error: string | null;
  selectedSensorId: string | null;
  onSelect: (sensorId: string | null) => void;
  onAddSensor: () => void;
  onOpenDetail: () => void;
}) {
  return <section className="section-block sensor-fleet" aria-labelledby="sensor-fleet-heading">
    <div className="section-heading"><div><p className="overline">Sensors</p><h2 id="sensor-fleet-heading">Monitor your servers</h2><p className="section-description">Each monitored server runs its own agent and sends aggregated network states to Sentinel. The central service never captures the remote interface directly.</p></div><div className="section-heading-actions"><span className="section-note">{sensors.length} registered sensor{sensors.length === 1 ? "" : "s"}</span><button onClick={onAddSensor}>Add sensor</button></div></div>

    {error ? <div className="empty-state sensor-empty"><span className="empty-mark">!</span><div><strong>Sensor fleet unavailable.</strong><p>{error}</p><p>Retry the connection before treating the fleet as empty.</p></div></div> : sensors.length === 0 ? <div className="empty-state sensor-empty"><span className="empty-mark">—</span><div><strong>No sensors registered yet.</strong><p>Add a sensor to open the guided install, register, start, heartbeat, and telemetry verification flow.</p><button onClick={onAddSensor}>Add your first sensor</button></div></div> : <div className="sensor-list">{sensors.map((sensor) => {
      const selected = selectedSensorId === sensor.sensor_id;
      return <article className={`sensor-card sensor-${sensor.status.toLowerCase()} ${selected ? "sensor-selected" : ""}`} key={sensor.sensor_id}>
        <button className="sensor-select" onClick={() => onSelect(selected ? null : sensor.sensor_id)} aria-pressed={selected}>
          <div className="sensor-card-top"><div><span className="sensor-status">{sensor.status}</span><h3>{sensor.hostname}</h3><code>{sensor.sensor_id}</code></div><span className="sensor-agent">AGENT {sensor.agent_version}</span></div>
          <div className="sensor-health-strip" aria-label="Sensor health"><span className={`health-${healthValue(sensor, "agent").toLowerCase()}`}><small>Agent</small><strong>{healthValue(sensor, "agent")}</strong></span><span className={`health-${(sensor.capture_status || "unknown").toLowerCase()}`}><small>Capture</small><strong>{sensor.capture_status || "UNKNOWN"}</strong></span><span className={`health-${(sensor.connection_status || "unknown").toLowerCase()}`}><small>Connection</small><strong>{sensor.connection_status || "UNKNOWN"}</strong></span><span className={`health-${healthValue(sensor, "telemetry").toLowerCase()}`}><small>Telemetry</small><strong>{healthValue(sensor, "telemetry")}</strong></span><span className={`health-${healthValue(sensor, "forecast").toLowerCase()}`}><small>Forecast</small><strong>{healthValue(sensor, "forecast")}</strong></span></div>
          {sensor.latest_warning && sensor.status === "ONLINE" && <div className="sensor-warning">PREDICTIVE WARNING · +10s score meets threshold</div>}
          <div className="sensor-facts"><span><small>Last heartbeat</small><strong>{freshness(sensor.heartbeat_freshness_seconds)}</strong></span><span><small>Last telemetry</small><strong>{freshness(sensor.telemetry_freshness_seconds)}</strong></span><span><small>States</small><strong>{sensor.state_count ?? sensor.runtime?.state_count ?? 0}</strong></span><span><small>History</small><strong>{sensor.history_length ?? sensor.runtime?.history_length ?? 0} / {sensor.history_required ?? sensor.runtime?.history_required ?? 10}</strong></span></div>
        </button>
        {selected && <div className="sensor-card-footer"><span>Selected sensor · detail is scoped to this server.{sensor.source_status ? ` Source status: ${sensor.source_status}.` : ""}{sensor.agent_last_error ? ` Last agent error: ${sensor.agent_last_error}` : ""}</span><button onClick={onOpenDetail}>Open sensor detail</button></div>}
        <details className="technical-details"><summary>Technical details</summary><p>Accepted sequence {sensor.last_accepted_sequence ?? sensor.last_sequence ?? 0} · last sent {sensor.last_sent_sequence ?? 0} · buffered batches {sensor.buffered_item_count ?? 0} · buffered bytes {sensor.buffered_bytes ?? 0}.</p></details>
      </article>;
    })}</div>}
  </section>;
}
