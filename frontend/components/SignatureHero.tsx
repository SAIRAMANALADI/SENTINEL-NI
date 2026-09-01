import type { ForecastPayload, LiveResponse, RuntimeStatus } from "../lib/types";

type Props = {
  forecast?: ForecastPayload;
  live: LiveResponse | null;
  mode: string;
  status: RuntimeStatus | string;
  onReplay: () => void;
  onLive: () => void;
  loading: boolean;
};

export function SignatureHero({ forecast, mode, onReplay, onLive, loading }: Props) {
  const active = Boolean(forecast?.horizons?.length);
  return <section className={`signature-hero ${active ? "is-active" : ""}`} aria-label="Network intelligence overview">
    <div className="signature-copy">
      <h1>Predict network behavior<br /><em>before it becomes</em><br />an operational problem.</h1>
      <p>Sentinel observes network activity, builds 10-second network states, and forecasts future network behavior.</p>
      <div className="hero-actions"><button onClick={onReplay} disabled={loading}>{loading ? "Running demo…" : "Run demo"}</button><button className="button-quiet" onClick={onLive}>Start live monitoring</button></div>
    </div>
    <div className="signal-field" aria-label={`${mode} network activity process`}>
      <div className="field-caption"><span>How Sentinel works</span><span>{active ? "Forecast available" : "Waiting for network data"}</span></div>
      <div className="network-process" role="img" aria-label="Traffic becomes flows, network states, and a forecast">
        <div className="process-step"><span>Traffic</span><small>network activity</small></div><b>→</b><div className="process-step"><span>Flows</span><small>grouped activity</small></div><b>→</b><div className="process-step"><span>Network states</span><small>10-second intervals</small></div><b>→</b><div className="process-step process-output"><span>Forecast</span><small>future behavior</small></div>
      </div>
      <p className="signal-empty">{active ? mode === "REMOTE SENSOR" ? "Telemetry from the selected remote server is ready to review." : "Prepared demonstration traffic is ready to review." : "Start a demo, select a connected server, or start live monitoring to see network activity here."}</p>
      {forecast?.horizons?.[0] && <div className="signature-readout"><span>Forecast Score · +10s</span><strong>{forecast.horizons[0].score.toFixed(4)}</strong><em>{forecast.horizons[0].warning ? "Predictive warning" : "No predictive warning"}</em></div>}
    </div>
  </section>;
}
