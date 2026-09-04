import { timingSafeEqual, randomBytes } from "node:crypto";
import type { NextRequest } from "next/server";

export type DashboardRole = "viewer" | "operator" | "admin";
export type DashboardSession = { role: DashboardRole; expiresAt: number };

export const DASHBOARD_SESSION_COOKIE = "sih_dashboard_session";
const DEFAULT_TTL_SECONDS = 8 * 60 * 60;
const storeKey = Symbol.for("sih26.dashboard.sessions");
type SessionStore = Map<string, DashboardSession>;

function sessionStore(): SessionStore {
  const globalState = globalThis as typeof globalThis & { [storeKey]?: SessionStore };
  if (!globalState[storeKey]) globalState[storeKey] = new Map();
  return globalState[storeKey]!;
}

export function dashboardAuthEnabled(): boolean {
  if (process.env.SIH_ENV === "production") return true;
  if (process.env.SIH_DASHBOARD_AUTH_ENABLED !== undefined) return process.env.SIH_DASHBOARD_AUTH_ENABLED === "true";
  return process.env.SIH_AUTH_ENABLED === "true" || process.env.SIH_ENV === "production";
}

export function dashboardSessionTtlSeconds(): number {
  const parsed = Number.parseInt(process.env.DASHBOARD_SESSION_TTL_SECONDS || "", 10);
  return Number.isFinite(parsed) && parsed >= 300 && parsed <= 24 * 60 * 60 ? parsed : DEFAULT_TTL_SECONDS;
}

export function configuredRoleTokens(): Record<DashboardRole, string> {
  return {
    viewer: process.env.SIH_VIEWER_TOKEN || "",
    operator: process.env.SIH_OPERATOR_TOKEN || "",
    admin: process.env.SIH_ADMIN_TOKEN || "",
  };
}

export function configuredRole(roleToken: string): DashboardRole | null {
  const candidate = Buffer.from(roleToken);
  if (!roleToken) return null;
  for (const role of ["admin", "operator", "viewer"] as const) {
    const configured = configuredRoleTokens()[role];
    const expected = Buffer.from(configured);
    if (expected.length === candidate.length && timingSafeEqual(expected, candidate)) return role;
  }
  return null;
}

export function hasConfiguredRoleTokens(): boolean {
  const tokens = configuredRoleTokens();
  return Boolean(tokens.viewer && tokens.operator && tokens.admin);
}

export function createDashboardSession(role: DashboardRole): { id: string; session: DashboardSession } {
  const id = randomBytes(32).toString("base64url");
  const session = { role, expiresAt: Date.now() + dashboardSessionTtlSeconds() * 1000 };
  sessionStore().set(id, session);
  return { id, session };
}

export function sessionId(request: NextRequest): string | null {
  return request.cookies.get(DASHBOARD_SESSION_COOKIE)?.value || null;
}

export function getDashboardSession(id: string | null): DashboardSession | null {
  if (!id) return null;
  const session = sessionStore().get(id);
  if (!session || session.expiresAt <= Date.now()) {
    if (session) sessionStore().delete(id);
    return null;
  }
  return session;
}

export function deleteDashboardSession(id: string | null): void {
  if (id) sessionStore().delete(id);
}

export function secureCookie(request: NextRequest): boolean {
  return process.env.NODE_ENV === "production" || request.nextUrl.protocol === "https:" || request.headers.get("x-forwarded-proto") === "https";
}

export function sameOrigin(request: NextRequest): boolean {
  const origin = request.headers.get("origin");
  const fetchSite = request.headers.get("sec-fetch-site");
  if (!origin) return fetchSite === "same-origin";
  return origin === request.nextUrl.origin;
}
