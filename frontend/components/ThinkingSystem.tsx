const stages = [
  ["Traffic", "network activity", "Observed traffic enters through the configured adapter."],
  ["Flows", "grouped activity", "Traffic is organized into flow-level activity."],
  ["Network states", "10-second intervals", "Flow activity becomes a network state."],
  ["History", "10 recent states", "Recent states provide temporal context for the forecast."],
  ["Forecast", "+10s to +50s", "Forecast Score is compared with the configured threshold."],
  ["Candidate sources", "evidence ranking", "Recent activity is ranked without claiming attribution."],
  ["Recommendations", "review only", "The operator receives a response recommendation; no block is applied."],
];

export function ThinkingSystem() {
  return <section className="thinking-system" aria-labelledby="thinking-heading"><div className="section-heading"><div><p className="overline">How it works</p><h2 id="thinking-heading">Traffic → Flows → Network states → Forecast</h2></div><span className="section-note">Select a step for more detail</span></div><div className="thinking-track">{stages.map(([name, meta, copy], index) => <details className="thinking-stage" key={name} open={index === 4}><summary><span className="stage-name">{name}</span><span className="stage-meta">{meta}</span><span className="stage-chevron">+</span></summary><p>{copy}</p></details>)}</div></section>;
}
