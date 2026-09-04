import { NextRequest, NextResponse } from "next/server";
import { configuredRole, createDashboardSession, DASHBOARD_SESSION_COOKIE, dashboardAuthEnabled, dashboardSessionTtlSeconds, hasConfiguredRoleTokens, secureCookie, sameOrigin } from "../../../../lib/dashboard-session";

export async function POST(request: NextRequest) {
  if (!sameOrigin(request)) return NextResponse.json({ error: { code: "CSRF_ORIGIN_MISMATCH", message: "request origin was rejected" } }, { status: 403 });
  if (!dashboardAuthEnabled()) return NextResponse.json({ authenticated: true, role: "development" });
  if (!hasConfiguredRoleTokens()) return NextResponse.json({ error: { code: "DASHBOARD_AUTH_MISCONFIGURED", message: "dashboard authentication is unavailable" } }, { status: 503 });
  let payload: unknown;
  try { payload = await request.json(); } catch { payload = null; }
  const token = payload && typeof payload === "object" && "token" in payload && typeof payload.token === "string" ? payload.token : "";
  const role = configuredRole(token);
  if (!role) return NextResponse.json({ error: { code: "INVALID_CREDENTIALS", message: "credentials were not accepted" } }, { status: 401 });
  const { id } = createDashboardSession(role);
  const response = NextResponse.json({ authenticated: true, role }, { headers: { "Cache-Control": "no-store" } });
  response.cookies.set({ name: DASHBOARD_SESSION_COOKIE, value: id, httpOnly: true, sameSite: "strict", secure: secureCookie(request), path: "/", maxAge: dashboardSessionTtlSeconds() });
  return response;
}
