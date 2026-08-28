# Operations guide

## Signals

- `GET /health/live` checks process liveness.
- `GET /health/ready` checks database connectivity.
- `GET /metrics` exposes Prometheus text format. Scrape it from a private network and attach service/environment labels at the scrape configuration layer.

## Safe rollout

1. Publish immutable API and web images from a tagged commit.
2. Apply the staging Kustomize overlay and run the smoke script.
3. Compare DORA metrics and error rate with the previous window.
4. Promote the same image digest, not a rebuilt image.
5. Keep the rollback target available until the first healthy metric window completes.

## Database

The first release uses SQLAlchemy `create_all` for a deliberately small schema. Before a multi-team production rollout, add Alembic migrations, automated backups, restore drills, and retention policies for audit payloads.

