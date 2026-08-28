# Contributing

Thanks for improving DeployLedger. Small, focused pull requests are easiest to review.

## Development loop

1. Create a branch from `main`.
2. Copy `.env.example` to `.env` only when running locally.
3. Run `make check` before opening a pull request.
4. Describe the operational trade-off in the pull request body, especially for schema, auth, or metric changes.

Backend changes should include an API test. Frontend changes should include a focused interaction test when behavior changes. Keep demo fixtures deterministic so screenshots and reviews remain reproducible.

