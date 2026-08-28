.PHONY: api-install api-test api-lint web-install web-check web-build check compose-up

api-install:
	python -m pip install -e './services/api[dev]'

api-test:
	python -m pytest -q services/api/tests

api-lint:
	ruff check services/api
	ruff format --check services/api

web-install:
	npm --prefix apps/web ci

web-check:
	npm --prefix apps/web run typecheck
	npm --prefix apps/web test

web-build:
	npm --prefix apps/web run build

check: api-lint api-test web-check web-build

compose-up:
	docker compose up --build

