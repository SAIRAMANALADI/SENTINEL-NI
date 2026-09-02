import type { DemoResponse, LiveResponse, SensorSummary } from "./types";

const token = process.env.NEXT_PUBLIC_SIH_API_TOKEN;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    cache: "no-store",
    headers: {
      Accept: "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers || {}),
    },
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Backend returned ${response.status}: ${detail || response.statusText}`);
  }
  return (await response.json()) as T;
}

export function getLive(): Promise<LiveResponse> {
  return request<LiveResponse>("/api/v1/live");
}

export function getReady(): Promise<{ ready: boolean; service_state: string }> {
  return request<{ ready: boolean; service_state: string }>("/api/v1/ready");
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

export function getSensors(): Promise<{ count: number; sensors: SensorSummary[] }> {
  return request<{ count: number; sensors: SensorSummary[] }>("/api/v1/sensors");
}
