import { NextRequest, NextResponse } from "next/server";
import { dashboardAuthEnabled, getDashboardSession, sessionId, sameOrigin, configuredRoleTokens, type DashboardRole } from "../../../lib/dashboard-session";

type RouteContext = { params: Promise<{ path: string[] }> };

const backendUrl = () => (process.env.BACKEND_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

function isAllowed(method: string, path: string): boolean {
  if (method === "GET") {
    return path === "/api/v1/ready" || path === "/api/v1/live" || path === "/api/v1/sensors" ||
      /^\/api\/v1\/sensors\/[^/]+(?:\/(?:forecast|health|sources|mitigation))?$/.test(path);
  }
  return method === "POST" && [
    "/api/v1/demo",
    "/api/v1/telemetry/start",
    "/api/v1/telemetry/stop",
  ].includes(path);
}

const roleLevel: Record<DashboardRole, number> = { viewer: 1, operator: 2, admin: 3 };

function requiredRole(method: "GET" | "POST", path: string): DashboardRole | null {
  if (method === "GET") return "viewer";
  if (method === "POST") return "operator";
  return null;
}

function authError(code: string, message: string, status: number) {
  return NextResponse.json({ error: { code, message } }, { status });
}

async function proxy(request: NextRequest, context: RouteContext, method: "GET" | "POST") {
  const { path: segments } = await context.params;
  const path = `/api/${segments.join("/")}`;
  if (!isAllowed(method, path)) {
    return NextResponse.json({ error: { code: "NOT_FOUND", message: "resource was not found" } }, { status: 404 });
  }

  if (method === "POST" && !sameOrigin(request)) return authError("CSRF_ORIGIN_MISMATCH", "request origin was rejected", 403);

  const headers = new Headers({ Accept: "application/json" });
  let token = process.env.SIH_API_TOKEN;
  const minimumRole = requiredRole(method, path);
  if (dashboardAuthEnabled() && minimumRole) {
    const session = getDashboardSession(sessionId(request));
    if (!session) return authError("DASHBOARD_AUTH_REQUIRED", "dashboard authentication is required", 401);
    if (roleLevel[session.role] < roleLevel[minimumRole]) return authError("INSUFFICIENT_ROLE", "dashboard role is not permitted", 403);
    token = configuredRoleTokens()[session.role];
    if (!token) return authError("DASHBOARD_AUTH_MISCONFIGURED", "dashboard authentication is unavailable", 503);
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let body: ArrayBuffer | undefined;
  if (method === "POST") {
    body = await request.arrayBuffer();
    const contentType = request.headers.get("content-type");
    if (contentType) headers.set("Content-Type", contentType);
  }

  try {
    const response = await fetch(`${backendUrl()}${path}${request.nextUrl.search}`, {
      method,
      headers,
      body,
      cache: "no-store",
    });
    const responseHeaders = new Headers();
    const responseType = response.headers.get("content-type");
    if (responseType) responseHeaders.set("content-type", responseType);
    responseHeaders.set("cache-control", "no-store");
    return new NextResponse(response.body, { status: response.status, headers: responseHeaders });
  } catch {
    return NextResponse.json(
      { error: { code: "BACKEND_UNAVAILABLE", message: "processing service is unavailable" } },
      { status: 503 },
    );
  }
}

export async function GET(request: NextRequest, context: RouteContext) {
  return proxy(request, context, "GET");
}

export async function POST(request: NextRequest, context: RouteContext) {
  return proxy(request, context, "POST");
}
