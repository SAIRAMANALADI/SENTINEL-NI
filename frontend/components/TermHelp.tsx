export function TermHelp({ term, children }: { term: string; children: string }) {
  return <details className="term-help"><summary aria-label={`What is ${term}?`}>?</summary><div><strong>{term}</strong><p>{children}</p></div></details>;
}
