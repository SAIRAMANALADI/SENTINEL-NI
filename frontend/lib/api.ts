import type { DemoResponse, FleetHealth, LiveResponse, SensorForecastResponse, SensorSummary } from "./types";

export interface DashboardSessionResponse {
  authenticated: boolean;
  role?: "viewer" | "operator" | "admin" | "development";
}

export interface ReadyResponse {
  ready: boolean;
  service_state: string;
  checks?: Record<string, boolean>;
  reasons?: string[];
  request_id?: string;
}

export class DashboardUnauthorizedError extends Error {
  constructor() {
    super("Dashboard session expired");
    this.name = "DashboardUnauthorizedError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    cache: "no-store",
    headers: {
      Accept: "application/json",
      ...(init?.headers || {}),
    },
    credentials: "same-origin",
  });
  if (response.status === 401) throw new DashboardUnauthorizedError();
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Backend returned ${response.status}: ${detail || response.statusText}`);
  }
  return (await response.json()) as T;
}

export function getLive(): Promise<LiveResponse> {
  return request<LiveResponse>("/api/v1/live");
}

export async function getDashboardSession(): Promise<DashboardSessionResponse> {
  const response = await fetch("/api/auth/session", { cache: "no-store", credentials: "same-origin", headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error("Dashboard authentication status is unavailable");
  return (await response.json()) as DashboardSessionResponse;
}

export async function loginDashboard(token: string): Promise<DashboardSessionResponse> {
  const response = await fetch("/api/auth/login", { method: "POST", cache: "no-store", credentials: "same-origin", headers: { Accept: "application/json", "Content-Type": "application/json" }, body: JSON.stringify({ token }) });
  if (!response.ok) throw new Error(response.status === 401 ? "Credentials were not accepted" : "Dashboard authentication is unavailable");
  return (await response.json()) as DashboardSessionResponse;
}

export async function logoutDashboard(): Promise<void> {
  const response = await fetch("/api/auth/logout", { method: "POST", cache: "no-store", credentials: "same-origin", headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error("Dashboard sign-out failed");
}

export async function getReady(): Promise<ReadyResponse> {
  const response = await fetch("/api/v1/ready", {
    cache: "no-store",
    headers: { Accept: "application/json" },
    credentials: "same-origin",
  });
  if (response.status === 401) throw new DashboardUnauthorizedError();
  let payload: ReadyResponse | null = null;
  try {
    payload = (await response.json()) as ReadyResponse;
  } catch {
    payload = null;
  }
  if (response.status === 503 && payload && payload.ready === false) return payload;
  if (!response.ok) {
    throw new Error(`Backend returned ${response.status}: ${payload ? JSON.stringify(payload) : response.statusText}`);
  }
  if (!payload) throw new Error("Backend returned an invalid readiness response");
  return payload;
}

export function runDemo(): Promise<DemoResponse> {
  return request<DemoResponse>("/api/v1/demo", { method: "POST" });
}

export function startTelemetry(): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>("/api/v1/telemetry/start", { method: "POST" });
}

export function stopTelemetry(): Promise<Record<string, unknown>> {
  return request<Record<string, unknown>>("/api/v1/telemetry/stop", { method: "POST" });
}

export function getSensors(): Promise<{ count: number; sensors: SensorSummary[]; health?: FleetHealth }> {
  return request<{ count: number; sensors: SensorSummary[]; health?: FleetHealth }>("/api/v1/sensors");
}

export function getSensor(sensorId: string): Promise<SensorSummary> {
  return request<SensorSummary>(`/api/v1/sensors/${encodeURIComponent(sensorId)}`);
}

export function getSensorForecast(sensorId: string): Promise<SensorForecastResponse> {
  return request<SensorForecastResponse>(`/api/v1/sensors/${encodeURIComponent(sensorId)}/forecast`);
}
