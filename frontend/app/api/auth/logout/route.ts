import { NextRequest, NextResponse } from "next/server";
import { DASHBOARD_SESSION_COOKIE, deleteDashboardSession, sessionId, sameOrigin, secureCookie } from "../../../../lib/dashboard-session";

export async function POST(request: NextRequest) {
  if (!sameOrigin(request)) return NextResponse.json({ error: { code: "CSRF_ORIGIN_MISMATCH", message: "request origin was rejected" } }, { status: 403 });
  deleteDashboardSession(sessionId(request));
  const response = NextResponse.json({ authenticated: false }, { headers: { "Cache-Control": "no-store" } });
  response.cookies.set({ name: DASHBOARD_SESSION_COOKIE, value: "", httpOnly: true, sameSite: "strict", secure: secureCookie(request), path: "/", maxAge: 0 });
  return response;
}
