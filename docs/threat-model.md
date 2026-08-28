# Threat model

## Assets

- Deployment history and release metadata.
- API and webhook credentials.
- Audit integrity and metric correctness.
- Availability of the release-operations console.

## Trust boundaries

1. External GitHub/CI event producers to the webhook endpoint.
2. Browser clients to the API.
3. API process to the database.
4. Container runtime to the cluster/node.

## Controls in this release

- HMAC SHA-256 webhook verification with constant-time comparison.
- API-key authentication for mutating endpoints outside local mode.
- Payload size cap, strict Pydantic enums, and bounded query limits.
- SQLAlchemy parameterized queries and unique idempotency constraint.
- Non-root containers, dropped Linux capabilities, read-only roots, and `seccomp` defaults.
- Audit events linked by previous hash and event hash.
- Health probes and Prometheus metrics for detection.

## Residual risks and next steps

- The local API-key model is intentionally small; production should sit behind OIDC or a service-to-service identity layer.
- Hash-chain append is single-writer safe. Use a database lock/transaction policy or an external append-only stream when scaling writers horizontally.
- The dashboard should use a CSP and CSRF strategy when cookie authentication is introduced.
- Secrets in Kubernetes must come from an external secret manager; `secret.example.yaml` is a shape-only example.

