"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import CommandCenter from "./CommandCenter";
import { getDashboardSession, loginDashboard, logoutDashboard, type DashboardSessionResponse } from "../lib/api";

export default function AuthGate() {
  const [session, setSession] = useState<DashboardSessionResponse | null>(null);
  const [token, setToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const expireSession = useCallback(() => setSession({ authenticated: false }), []);

  useEffect(() => {
    void getDashboardSession().then(setSession).catch(() => setError("Dashboard authentication is unavailable")).finally(() => setLoading(false));
  }, []);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const nextSession = await loginDashboard(token);
      setToken("");
      setSession(nextSession);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Credentials were not accepted");
    } finally {
      setSubmitting(false);
    }
  };

  const signOut = async () => {
    try { await logoutDashboard(); setSession({ authenticated: false }); } catch (reason) { setError(reason instanceof Error ? reason.message : "Dashboard sign-out failed"); }
  };

  if (loading) return <main className="auth-shell"><div className="auth-card"><span className="overline">SENTINEL / NETWORK INTELLIGENCE</span><p>Checking dashboard access…</p></div></main>;
  if (session?.authenticated) return <CommandCenter role={session.role} onLogout={() => void signOut()} onUnauthorized={expireSession} />;

  return <main className="auth-shell"><form className="auth-card" onSubmit={submit}><span className="overline">SENTINEL / NETWORK INTELLIGENCE</span><h1>Sign in to Sentinel dashboard</h1><p>Use a configured Sentinel dashboard role token to continue. The credential is checked server-side and is never stored in the browser.</p><label htmlFor="dashboard-token">Dashboard role token</label><input id="dashboard-token" type="password" value={token} onChange={(event) => setToken(event.target.value)} autoComplete="current-password" required /><button type="submit" disabled={submitting}>{submitting ? "Checking access…" : "Sign in"}</button>{error && <div className="auth-error" role="alert">{error}</div>}</form></main>;
}
