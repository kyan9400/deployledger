# Architecture

```text
GitHub / CI / Argo CD
          │ signed deployment event or idempotent HTTP write
          ▼
     FastAPI service ───────────────► Prometheus scrape
       │       │
       │       ├── DORA query layer (windowed metrics + trends)
       │       └── append-only audit chain (SHA-256 links)
       ▼
 SQLite (local) / Postgres (shared)
          │
          ▼
 React dashboard (demo fixtures or live API)
```

The API is the source of truth for deployment records. A deployment is identified by its service and optional idempotency key; duplicate delivery attempts return the original record. Webhooks are authenticated before parsing the event and are capped at 1 MiB. Metrics are derived from the deployment ledger rather than emitted as a second mutable data model.

The frontend keeps a narrow data contract (`services`, `dora`, `deployments`) so the same artifact can be a static portfolio demo or a live operational console. In a hosted environment, put the API behind TLS and an identity-aware ingress, then set `VITE_API_URL` at build time.

