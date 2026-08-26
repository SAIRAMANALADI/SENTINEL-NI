import type { ForecastRow, Explanation, RuntimeStatus } from "../lib/types";
import { TermHelp } from "./TermHelp";

function score(value: number) {
  return Number.isFinite(value) ? value.toFixed(4) : "—";
}

export function ForecastView({ rows, threshold, explanation, status }: { rows: ForecastRow[]; threshold: number | null | undefined; explanation?: Explanation; status?: RuntimeStatus | string }) {
  const safeThreshold = typeof threshold === "number" ? threshold : 0;
  const maxScore = Math.max(safeThreshold * 1.25, ...rows.map((row) => row.score * 1.18), 0.4);
  const chartWidth = 900;
  const chartHeight = 286;
  const plotLeft = 54;
  const plotRight = 28;
  const plotTop = 32;
  const plotBottom = 48;
  const plotWidth = chartWidth - plotLeft - plotRight;
  const plotHeight = chartHeight - plotTop - plotBottom;
  const xFor = (index: number) => plotLeft + (rows.length === 1 ? plotWidth / 2 : (index / (rows.length - 1)) * plotWidth);
  const yFor = (value: number) => plotTop + (1 - value / maxScore) * plotHeight;
  const chartPoints = rows.map((row, index) => {
    const x = xFor(index);
    const y = yFor(row.score);
    return `${x},${y}`;
  }).join(" ");
  const areaPoints = `${plotLeft},${plotTop + plotHeight} ${chartPoints} ${plotLeft + plotWidth},${plotTop + plotHeight}`;
  const thresholdY = yFor(safeThreshold);
  const ticks = Array.from({ length: 5 }, (_, index) => (maxScore * index) / 4).reverse();
  const aboveThreshold = rows.filter((row) => row.warning).length;

  return (
    <section className="section-block" aria-labelledby="forecast-heading">
      <div className="section-heading"><div><p className="overline">Forecast</p><h2 id="forecast-heading">The next 50 seconds</h2></div><span className="section-note">+10s is primary · five forecast points <TermHelp term="Predictive Warning">Displayed when the Forecast Score meets the configured threshold. It does not mean an attack has been confirmed.</TermHelp></span></div>
      {rows.length ? (
        <>
          <div className="forecast-axis"><span>Now</span><span>Projected network states</span></div>
          <div className="forecast-rail">
            {rows.map((row, index) => (
              <div className={`forecast-item ${index === 0 ? "forecast-primary" : ""} ${row.warning ? "forecast-warning" : ""}`} key={`${row.step}-${row.timestamp}`}>
                <span className="forecast-label">+{row.horizon_seconds}s {index === 0 ? "· primary" : ""}</span>
                <strong>{score(row.score)}</strong>
                <span className="forecast-decision">{row.warning ? "Predictive warning" : "No predictive warning"}</span>
              </div>
            ))}
          </div>
          <div className="chart-frame">
            <div className="chart-header"><span>Forecast Score over time</span><span className="chart-readout">{aboveThreshold} of {rows.length} above threshold · {safeThreshold.toFixed(2)}</span></div>
            <svg className="forecast-chart" viewBox={`0 0 ${chartWidth} ${chartHeight}`} role="img" aria-label="Forecast score trajectory with readable score scale and operating threshold">
              <defs><linearGradient id="forecastArea" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#c4e96d" stopOpacity=".15" /><stop offset="1" stopColor="#c4e96d" stopOpacity="0" /></linearGradient></defs>
              <rect x={plotLeft} y={plotTop} width={plotWidth} height={Math.max(0, thresholdY - plotTop)} className="warning-zone" />
              {ticks.map((tick) => <g key={`tick-${tick}`}><line x1={plotLeft} y1={yFor(tick)} x2={plotLeft + plotWidth} y2={yFor(tick)} className="chart-grid-line" /><text x={plotLeft - 12} y={yFor(tick) + 4} textAnchor="end" className="chart-scale-label">{tick.toFixed(2)}</text></g>)}
              <line x1={plotLeft} y1={thresholdY} x2={plotLeft + plotWidth} y2={thresholdY} className="threshold-line" />
              <rect x={plotLeft + plotWidth - 102} y={thresholdY - 22} width="94" height="19" rx="2" className="threshold-tag" /><text x={plotLeft + plotWidth - 55} y={thresholdY - 9} textAnchor="middle" className="threshold-label">Threshold {safeThreshold.toFixed(2)}</text>
              {rows.map((row, index) => <line x1={xFor(index)} y1={plotTop} x2={xFor(index)} y2={plotTop + plotHeight} className="chart-guide" key={`guide-${row.step}`} />)}
              <polygon points={areaPoints} className="score-area" />
              <polyline points={chartPoints} className="score-line" />
              {rows.map((row, index) => <g key={`point-${row.step}`}><circle cx={xFor(index)} cy={yFor(row.score)} r={index === 0 ? 8 : 6} className={row.warning ? "score-point point-warning" : "score-point"} /><circle cx={xFor(index)} cy={yFor(row.score)} r="2.5" className="score-point-core" /><text x={xFor(index)} y={yFor(row.score) - 15} textAnchor="middle" className="point-value">{score(row.score)}</text><text x={xFor(index)} y={chartHeight - 18} textAnchor="middle" className="chart-axis-label">+{row.horizon_seconds}s</text></g>)}
              <text x={plotLeft} y={chartHeight - 3} className="origin-label">FORECAST ORIGIN</text>
            </svg>
            <div className="chart-legend"><span><i className="legend-score" /> Forecast Score</span><span><i className="legend-threshold" /> Threshold</span><span className="chart-meaning">Above the line = Predictive warning</span></div>
          </div>
          <p className="micro-copy">Why five horizons? Sentinel shows several future points so operators can see how the forecast changes over time. Forecast Score is a raw model output, not a calibrated probability.</p>
        </>
      ) : (
        <div className="empty-state"><span className="empty-mark">—</span><div><strong>{status === "STOPPED" ? "Waiting for network data" : status === "ERROR" ? "Forecast unavailable" : "Building forecast history"}</strong><p>{status === "STOPPED" ? "Run the demo or start live monitoring to produce a forecast." : status === "ERROR" ? "The backend did not provide a usable forecast." : "Forecast activates after 10 recent network states are available."}</p></div></div>
      )}
      {explanation && <Explainability explanation={explanation} />}
    </section>
  );
}

function Explainability({ explanation }: { explanation: Explanation }) {
  const top = explanation.top_features || [];
  const temporal = explanation.temporal_positions || [];
  return <div className="explain-block"><div className="section-heading compact"><div><p className="overline">Why this forecast?</p><h3>Model sensitivity</h3></div><span className="section-note">not a causal explanation</span></div><div className="explain-grid"><div className="signal-lead"><span className="overline">Top signal</span><strong>{top[0]?.feature || "Unavailable"}</strong><span>Sensitivity {typeof top[0]?.sensitivity === "number" ? top[0].sensitivity.toFixed(4) : "—"} · {top[0]?.time_position || "current state"}</span></div><div className="signal-list"><span className="overline">Other important signals</span>{top.slice(1, 4).map((item) => <span key={`${item.feature}-${item.time_position}`}>{item.feature}</span>)}</div><div className="temporal-list"><span className="overline">Temporal contribution</span>{temporal.slice(0, 3).map((item) => <span key={item.time_position}>{item.time_position}<i>{item.sensitivity.toFixed(4)}</i></span>)}</div></div><p className="micro-copy">Model sensitivity is not a causal explanation. A signal response does not establish attack cause or source identity.</p></div>;
}
