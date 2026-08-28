import type { DashboardData, Deployment, DORAResponse, Service } from "./types";

const service = (slug: string, name: string, team: string): Service => ({
  id: slug,
  slug,
  name,
  owner_team: team,
  repository: `https://github.com/kyan9400/${slug}`,
  created_at: "2026-01-01T00:00:00Z",
});

const services = [
  service("checkout-api", "Checkout API", "commerce-platform"),
  service("edge-web", "Edge Web", "experience"),
];

const now = Date.now();
const demoDeployments: Deployment[] = Array.from({ length: 18 }, (_, index) => {
  const failed = index === 3 || index === 11;
  const created = new Date(now - (17 - index) * 86_400_000 - (index % 3) * 3_600_000);
  const finished = new Date(created.getTime() + (12 + (index % 8)) * 60_000);
  return {
    id: `demo-${index}`,
    service_slug: services[index % services.length].slug,
    environment: index % 4 === 0 ? "staging" : "production",
    revision: `${(index + 1).toString(16).padStart(7, "0")}-release`,
    status: failed ? "failed" : "succeeded",
    source: index % 3 === 0 ? "github" : "argocd",
    change_kind: index === 3 || index === 11 ? "urgent" : "normal",
    started_at: created.toISOString(),
    finished_at: finished.toISOString(),
    recovered_at: failed ? new Date(finished.getTime() + 37 * 60_000).toISOString() : null,
    lead_time_seconds: 720 + index * 111,
    failure_reason: failed ? "Checkout provider timeout after release" : null,
    created_at: created.toISOString(),
  } as Deployment;
});

const trend = Array.from({ length: 30 }, (_, index) => ({
  date: new Date(now - (29 - index) * 86_400_000).toISOString().slice(0, 10),
  deployments: index % 5 === 0 ? 0 : 1 + (index % 3),
  failures: index === 8 || index === 20 ? 1 : 0,
  average_lead_time_seconds: 900 + (index % 6) * 140,
}));

const dora: DORAResponse = {
  window_days: 30,
  generated_at: new Date(now).toISOString(),
  service_slug: null,
  summary: {
    deployment_frequency_per_week: 4.7,
    change_lead_time_p50_seconds: 1360,
    change_lead_time_p95_seconds: 2480,
    change_fail_rate_percent: 7.4,
    failed_deployment_recovery_p50_seconds: 2220,
    deployment_rework_rate_percent: 3.7,
  },
  trend,
};

export const demoData: DashboardData = {
  services,
  dora,
  deployments: demoDeployments,
  demo: true,
};
