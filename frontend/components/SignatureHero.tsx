import type { ForecastPayload, LiveResponse, RuntimeStatus } from "../lib/types";

type Props = {
  forecast?: ForecastPayload;
  live: LiveResponse | null;
  mode: string;
  status: RuntimeStatus | string;
  onAddSensor: () => void;
  onSensors: () => void;
  onReplay: () => void;
  loading: boolean;
  canOperate?: boolean;
};

export function SignatureHero({ forecast, mode, onAddSensor, onSensors, onReplay, loading, canOperate = true }: Props) {
  const active = Boolean(forecast?.horizons?.length);
  return <section className={`signature-hero ${active ? "is-active" : ""}`} aria-label="Network intelligence overview">
    <div className="signature-copy">
      <p className="overline">Operator overview</p>
      <h1>Know which servers<br /><em>are ready to trust.</em></h1>
      <p>Connect a Sentinel agent, verify heartbeat and telemetry freshness, then review a current forecast with its evidence and recommendation context.</p>
      <div className="hero-actions"><button onClick={onAddSensor}>Add a sensor</button><button className="button-quiet" onClick={onSensors}>View sensors</button>{canOperate && <button className="text-button" onClick={onReplay} disabled={loading}>{loading ? "Loading replay…" : "Use Replay"}</button>}</div>
    </div>
    <div className="signal-field" aria-label={`${mode} network activity process`}>
      <div className="field-caption"><span>Operator path</span><span>{active ? "Forecast available" : "Waiting for sensor data"}</span></div>
      <div className="network-process" role="img" aria-label="Agent heartbeat and telemetry lead to sensor online, forecast, sources, and mitigation">
        <div className="process-step"><span>Agent</span><small>install + start</small></div><b>→</b><div className="process-step"><span>Heartbeat</span><small>process health</small></div><b>→</b><div className="process-step"><span>Telemetry</span><small>fresh network states</small></div><b>→</b><div className="process-step process-output"><span>Sensor online</span><small>forecast and evidence</small></div>
      </div>
      <p className="signal-empty">{active ? "Current sensor telemetry is ready to review." : "Add a sensor and run the agent on the monitored server. This page will reflect the central status as it changes."}</p>
      {forecast?.horizons?.[0] && <div className="signature-readout"><span>Forecast Score · +10s</span><strong>{forecast.horizons[0].score.toFixed(4)}</strong><em>{forecast.horizons[0].warning ? "Predictive warning" : "No predictive warning"}</em></div>}
    </div>
  </section>;
}
