# Runbook: high change fail rate

Use this when `change_fail_rate_percent` rises above the team's agreed threshold.

## Triage

1. Confirm the window and service scope in `/api/v1/metrics/dora`.
2. Check `/api/v1/deployments?status=failed` and group by `failure_reason`, environment, and source.
3. Compare the last successful revision and the failed revision in the originating CI system.
4. Check whether failures cluster around one environment, owner team, or urgent change kind.

## Stabilize

- Pause non-essential production promotion.
- Roll back the smallest safe unit using the deployment system of record.
- Keep one canary path open if it can produce a clean signal.
- Record the incident and link the deployment IDs in the audit trail.

## Learn

After recovery, add a regression test or validation gate, update the failure reason taxonomy, and review whether deployment automation can make the safe path the default. Avoid optimizing the metric by hiding failures; the useful signal is the one that remains trustworthy.

