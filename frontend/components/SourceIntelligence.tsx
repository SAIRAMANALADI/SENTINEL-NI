import type { MitigationRecommendation, SourcePriority } from "../lib/types";
import { TermHelp } from "./TermHelp";

function activity(row: SourcePriority) {
  const values = row.activity_features || row;
  return `${values.packet_count ?? "—"} packets · ${typeof values.byte_count === "number" ? values.byte_count.toFixed(0) : "—"} bytes · ${values.unique_destinations ?? "—"} destinations`;
}

function priorityLabel(priority: string) {
  if (priority.startsWith("HIGH")) return "High";
  if (priority.startsWith("MEDIUM")) return "Medium";
  if (priority.startsWith("LOW")) return "Low";
  return priority;
}

export function SourceIntelligence({ sources, recommendations }: { sources: SourcePriority[]; recommendations: MitigationRecommendation[] }) {
  return <>
    <section className="section-block" aria-labelledby="sources-heading"><div className="section-heading"><div><p className="overline">Candidate sources</p><h2 id="sources-heading">Sources to review <TermHelp term="Candidate Source">A source whose recent activity contributes strongly to the ranking. It is not confirmed attacker attribution.</TermHelp></h2><p className="section-description">Recent activity is ranked to help an operator focus an investigation.</p></div></div><div className="source-list">{sources.length ? sources.slice(0, 6).map((source, index) => { const priority = source.priority || "LOW PRIORITY SOURCE"; const tone = priority.startsWith("HIGH") ? "source-high" : priority.startsWith("MEDIUM") ? "source-medium" : "source-low"; return <article className={`source-row ${tone}`} key={source.source_ip}><span className="source-rank">{index + 1}</span><div className="source-main"><strong>{source.source_ip}</strong><span className="source-evidence">{source.measured_reasons || "Measured activity only"}</span><span className="source-meta">{activity(source)}</span></div><span className="source-priority" aria-label={`${priorityLabel(priority)} priority`}>{priorityLabel(priority)}</span></article>; }) : <div className="empty-state"><span className="empty-mark">—</span><div><strong>No candidate sources</strong><p>No current source activity is available from the backend.</p></div></div>}</div><p className="micro-copy">Candidate sources are ranked evidence, not confirmed attribution.</p></section>
    <section className="section-block response-block" aria-labelledby="response-heading"><div className="response-banner"><div><p className="overline">Recommendations</p><h2 id="response-heading">Review the next action <TermHelp term="Mitigation">A defensive recommendation generated from current network context. It is simulation/recommendation only.</TermHelp></h2><p className="section-description">Recommendations are for operator review. Sentinel does not automatically block traffic.</p></div><div className="simulation-lock">Simulation only <strong>TRUE</strong><span>Automatic blocking disabled</span></div></div><div className="response-list">{recommendations.length ? recommendations.slice(0, 6).map((item) => <article className="response-row" key={item.source_ip}><div><strong>{item.source_ip}</strong><span>{priorityLabel(item.priority)}</span></div><p>{item.recommendation}</p><small>Recommendation only · no traffic policy changed</small></article>) : <p className="micro-copy">No mitigation recommendation is currently available.</p>}</div></section>
  </>;
}
