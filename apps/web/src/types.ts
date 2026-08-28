export type Service = {
  id: string;
  slug: string;
  name: string;
  owner_team: string;
  repository: string;
  created_at: string;
};

export type Deployment = {
  id: string;
  service_slug: string;
  environment: "production" | "staging" | "preview";
  revision: string;
  status: "running" | "succeeded" | "failed" | "rolled_back";
  source: "api" | "github" | "argocd" | "terraform";
  change_kind: "normal" | "urgent";
  started_at: string;
  finished_at: string | null;
  recovered_at: string | null;
  lead_time_seconds: number | null;
  failure_reason: string | null;
  created_at: string;
};

export type DORASummary = {
  deployment_frequency_per_week: number;
  change_lead_time_p50_seconds: number | null;
  change_lead_time_p95_seconds: number | null;
  change_fail_rate_percent: number;
  failed_deployment_recovery_p50_seconds: number | null;
  deployment_rework_rate_percent: number;
};

export type DORATrendPoint = {
  date: string;
  deployments: number;
  failures: number;
  average_lead_time_seconds: number | null;
};

export type DORAResponse = {
  window_days: number;
  generated_at: string;
  service_slug: string | null;
  summary: DORASummary;
  trend: DORATrendPoint[];
};

export type DashboardData = {
  services: Service[];
  dora: DORAResponse;
  deployments: Deployment[];
  demo: boolean;
};
