type Tone = "live" | "ready" | "warning" | "stale" | "muted" | "error";

export function StatusPill({ label, tone = "muted" }: { label: string; tone?: Tone }) {
  return <span className={`status-pill status-${tone}`}><span className="status-dot" />{label}</span>;
}
