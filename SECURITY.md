# Security policy

## Supported versions

The latest release on the default branch is supported. Older releases may not receive security fixes.

## Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability. Use GitHub's private vulnerability reporting for this repository, or email the maintainer through the address on the GitHub profile with the subject `DeployLedger security`. Include reproduction steps, impact, and a safe way to contact you.

DeployLedger is intended to run behind TLS and an authenticated ingress in production. Never commit API keys, webhook secrets, cloud credentials, or real deployment payloads.

