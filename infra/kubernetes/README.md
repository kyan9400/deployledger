# Kubernetes deployment

The base uses two replicas, health probes, resource budgets, non-root security contexts, and an ingress split between `/api`, `/health`, and the static dashboard. Use the dev overlay for a single-replica cluster and staging for a namespaced release.

```bash
kubectl apply -k infra/kubernetes/overlays/dev
kubectl -n deployledger rollout status deploy/deployledger-api
kubectl -n deployledger rollout status deploy/deployledger-web
```

Copy `base/secret.example.yaml` to a secret-manager workflow; do not commit real values.

