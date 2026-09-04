"use client";

import { useMemo, useState } from "react";
import type { MitigationRecommendation, SourcePriority } from "../lib/types";
import { TermHelp } from "./TermHelp";

function activity(row: SourcePriority) {
  const values = row.recent_activity || row.activity_features || row;
  return `${values.packet_count ?? "—"} packets · ${typeof values.byte_count === "number" ? values.byte_count.toFixed(0) : "—"} bytes · ${values.unique_destinations ?? "—"} destinations`;
}

function priorityLabel(priority: string) {
  if (priority.startsWith("HIGH")) return "High";
  if (priority.startsWith("MEDIUM")) return "Medium";
  if (priority.startsWith("LOW")) return "Low";
  return priority;
}

function percent(value?: number) {
  return typeof value === "number" ? `${value >= 0 ? "+" : ""}${(value * 100).toFixed(0)}%` : "—";
}

function seen(value?: string) {
  return value ? new Date(value).toLocaleString([], { dateStyle: "short", timeStyle: "medium" }) : "—";
}

export function SourceIntelligence({
  sources,
  recommendations,
  sensorId,
}: {
  sources: SourcePriority[];
  recommendations: MitigationRecommendation[];
  sensorId?: string;
}) {
  const [selectedIp, setSelectedIp] = useState<string | null>(null);
  const selected = useMemo(() => sources.find((source) => source.source_ip === selectedIp) || sources[0] || null, [selectedIp, sources]);

  return <>
    <section className="section-block" aria-labelledby="sources-heading">
      <div className="section-heading"><div><p className="overline">Candidate sources</p><h2 id="sources-heading">Sources to review <TermHelp term="Candidate Source">A source whose recent activity contributes strongly to the ranking. It is not confirmed source attribution.</TermHelp></h2><p className="section-description">Recent activity is ranked to help an operator focus an investigation. {sensorId ? `Scoped to ${sensorId}.` : ""}</p></div><span className="section-note">{sources.length ? `${sources.length} ranked` : "no source data"}</span></div>
      <div className="source-layout">
        <div className="source-list">{sources.length ? sources.slice(0, 8).map((source, index) => { const priority = source.priority || "LOW PRIORITY SOURCE"; const tone = priority.startsWith("HIGH") ? "source-high" : priority.startsWith("MEDIUM") ? "source-medium" : "source-low"; return <button className={`source-row ${tone} ${selected?.source_ip === source.source_ip ? "source-selected" : ""}`} key={`${source.source_ip}-${source.interval_start || index}`} onClick={() => setSelectedIp(source.source_ip)} aria-pressed={selected?.source_ip === source.source_ip}><span className="source-rank">{index + 1}</span><span className="source-main"><strong>{source.source_ip}</strong><span className="source-evidence">{source.measured_reasons || "Measured activity only"}</span><span className="source-meta">{activity(source)} · last seen {seen(source.last_seen)}</span></span><span className="source-priority" aria-label={`${priorityLabel(priority)} priority`}>{priorityLabel(priority)}</span></button>; }) : <div className="empty-state"><span className="empty-mark">—</span><div><strong>No candidate sources</strong><p>No source activity is available for this sensor.</p></div></div>}</div>
        {selected && <aside className="source-detail" aria-label={`Candidate source details for ${selected.source_ip}`}><p className="overline">Selected Candidate Source</p><h3>{selected.source_ip}</h3><span className={`source-priority ${selected.priority.startsWith("HIGH") ? "source-high" : selected.priority.startsWith("MEDIUM") ? "source-medium" : "source-low"}`}>{priorityLabel(selected.priority)} · {selected.priority_points ?? 0} points</span><dl><div><dt>Activity</dt><dd>{activity(selected)}</dd></div><div><dt>Trend</dt><dd>Flows {percent(selected.flow_growth)} · packets {percent(selected.packet_growth)}</dd></div><div><dt>Destinations / ports</dt><dd>{selected.unique_destinations ?? "—"} / {selected.unique_destination_ports ?? "—"}</dd></div><div><dt>First seen</dt><dd>{seen(selected.first_seen)}</dd></div><div><dt>Last seen</dt><dd>{seen(selected.last_seen)}</dd></div><div><dt>Forecast context</dt><dd>{selected.forecast_context?.network_warning ? "Network warning active" : selected.forecast_context?.available ? `Forecast Score ${selected.forecast_context.forecast_score ?? "—"}` : "Unavailable"}</dd></div></dl><p className="source-evidence">{selected.measured_reasons || "Measured activity only"}</p></aside>}
      </div>
      <p className="micro-copy">Candidate sources are ranked evidence, not confirmed attribution. Source identity remains scoped to the parent sensor.</p>
    </section>
    <section className="section-block response-block" aria-labelledby="response-heading"><div className="response-banner"><div><p className="overline">Recommendations</p><h2 id="response-heading">Review the next action <TermHelp term="Mitigation">A defensive recommendation generated from current network context. It is simulation/recommendation only.</TermHelp></h2><p className="section-description">Recommendations are for operator review. Sentinel does not automatically block traffic.</p></div><div className="simulation-lock">Simulation only <strong>TRUE</strong><span>Automatic blocking disabled</span></div></div><div className="response-list">{recommendations.length ? recommendations.slice(0, 8).map((item) => <article className="response-row" key={item.source_ip}><div><strong>{item.source_ip}</strong><span>{priorityLabel(item.priority)}</span></div><p>{item.recommendation}</p><small>Recommendation only · no traffic policy changed</small></article>) : <p className="micro-copy">No mitigation recommendation is currently available.</p>}</div></section>
  </>;
}
