import { demoData } from "./data";
import type { DashboardData, Deployment, DORAResponse, Service } from "./types";

const baseURL = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "");

async function getJSON<T>(path: string): Promise<T> {
  const response = await fetch(`${baseURL}${path}`, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`API returned ${response.status}`);
  return response.json() as Promise<T>;
}

export async function loadDashboard(serviceSlug: string | null = null): Promise<DashboardData> {
  if (!baseURL) return demoData;
  const query = serviceSlug ? `?service_slug=${encodeURIComponent(serviceSlug)}` : "";
  const [services, dora, deployments] = await Promise.all([
    getJSON<Service[]>("/api/v1/services"),
    getJSON<DORAResponse>(`/api/v1/metrics/dora${query}`),
    getJSON<Deployment[]>(`/api/v1/deployments${query ? `${query}&limit=25` : "?limit=25"}`),
  ]);
  return { services, dora, deployments, demo: false };
}
