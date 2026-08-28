# DeployLedger

[![CI](https://github.com/kyan9400/deployledger/actions/workflows/ci.yml/badge.svg)](https://github.com/kyan9400/deployledger/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/kyan9400/deployledger?display_name=tag)](https://github.com/kyan9400/deployledger/releases)
[![License](https://img.shields.io/badge/license-MIT-0f766e.svg)](LICENSE)

DeployLedger is a self-hosted release-operations control plane for teams that want one calm, auditable view of delivery speed and change stability. It ingests deployment events, computes DORA metrics, exposes Prometheus health signals, and gives engineers a small dashboard for deciding whether the next release is safe to ship.

The project is deliberately shaped like a production service: async FastAPI + SQLAlchemy, a responsive React dashboard, signed GitHub webhooks, idempotent writes, a tamper-evident audit chain, container hardening, Kubernetes manifests, Terraform infrastructure, and CI that tests code and scans images.

## What it demonstrates

| Area | Implementation |
| --- | --- |
| Backend | FastAPI, Pydantic v2, async SQLAlchemy, SQLite for local work and Postgres for deployment |
| Product UI | React + Vite dashboard with service scoping, trend visualization, environment matrix, release feed, and explicit demo/live state |
| Reliability | Liveness/readiness probes, Prometheus exposition, request latency histogram, deterministic seed data |
| Security | HMAC GitHub webhook verification, constant-time API-key checks, body-size limits, non-root images, read-only filesystems |
| Platform engineering | Docker Compose, Kustomize overlays, ECS/Fargate Terraform blueprint, release workflow, runbooks, Backstage catalog metadata |

## DORA view

DeployLedger models the current five-metric DORA model: change lead time, deployment frequency, failed deployment recovery time, change fail rate, and deployment rework rate. The definitions are kept close to the service code and the dashboard surfaces the window used for each calculation. See [DORA's metric guide](https://dora.dev/guides/dora-metrics/) and [the history of the model](https://dora.dev/insights/dora-metrics-history/) for the underlying research.

## Quick start

### Local API

```powershell
cd services/api
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
$env:DEPLOYLEDGER_DEMO_SEED = "true"
uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs`. The default local database is `deployledger.db`; set `DEPLOYLEDGER_DATABASE_URL` to an async Postgres URL when you need a shared environment.

### Dashboard

```powershell
cd apps/web
npm install
npm run dev
```

The dashboard is intentionally usable without an API: when `VITE_API_URL` is absent it renders deterministic demo data and labels itself as Demo mode. Set `VITE_API_URL=http://localhost:8000` to use the live API.

### Full stack with containers

```powershell
copy .env.example .env
docker compose up --build
```

The dashboard is at `http://localhost:4173`, the API is at `http://localhost:8000`, and Postgres is persisted in the `deployledger-postgres` volume. The Compose defaults are for local development only.

## API shape

- `GET /api/v1/services` — service catalog.
- `POST /api/v1/services` — register a service (API key required outside local mode).
- `GET /api/v1/deployments` — filter deployment history by service, environment, or status.
- `POST /api/v1/deployments` — ingest a deployment; repeat a request safely with `Idempotency-Key`.
- `PATCH /api/v1/deployments/{id}` — close a running deployment or record recovery details.
- `GET /api/v1/metrics/dora?window_days=30` — current DORA summary and daily trend.
- `GET /api/v1/audit` — newest entries from the append-only hash chain.
- `POST /api/v1/webhooks/github` — verify and ingest GitHub deployment events.

An importable OpenAPI sketch lives in [`docs/openapi.yaml`](docs/openapi.yaml). FastAPI also publishes a complete interactive schema in local environments.

## Operational notes

- Demo fixtures are opt-in (`DEPLOYLEDGER_DEMO_SEED=true`); production defaults to an empty database.
- The audit chain is tamper-evident for a single writer. For multi-writer production deployments, put writes behind one database transaction/locking policy and export events to an immutable sink.
- The Terraform module expects a pre-existing VPC, private subnets, security groups, and Secrets Manager values. It does not create network boundaries on your behalf.
- OpenTelemetry's [CI/CD semantic conventions](https://opentelemetry.io/docs/specs/semconv/cicd/) are a natural next ingestion adapter; the current HTTP contract is intentionally small enough to sit in front of an event collector.

## Engineering docs

- [Architecture](docs/architecture.md)
- [Threat model](docs/threat-model.md)
- [Operations](docs/operations.md)
- [High change-failure runbook](docs/runbooks/high-change-failure-rate.md)
- [Kubernetes deployment](infra/kubernetes/README.md)
- [Terraform deployment](infra/terraform/README.md)

## License

MIT. See [LICENSE](LICENSE).

