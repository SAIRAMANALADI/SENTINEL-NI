import { NextRequest, NextResponse } from "next/server";
import { dashboardAuthEnabled, getDashboardSession, sessionId } from "../../../../lib/dashboard-session";

export async function GET(request: NextRequest) {
  if (!dashboardAuthEnabled()) return NextResponse.json({ authenticated: true, role: "development" }, { headers: { "Cache-Control": "no-store" } });
  const session = getDashboardSession(sessionId(request));
  return NextResponse.json(session ? { authenticated: true, role: session.role } : { authenticated: false }, { headers: { "Cache-Control": "no-store" } });
}
