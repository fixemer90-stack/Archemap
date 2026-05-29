.DEFAULT_GOAL := help
SHELL := /bin/bash
BACKEND_DIR := backend
FRONTEND_DIR := frontend
CONTRACTS_DIR := contracts

.PHONY: help infra-up infra-down backend-dev frontend-dev db-migrate db-revision \
        test test-unit test-integration lint format typecheck \
        contracts-validate generate-client clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-24s\033[0m %s\n", $$1, $$2}'

# ── Infrastructure ──────────────────────────────────────────────────────────

infra-up: ## Start Docker Compose services (db, redis, etc.)
	docker compose up -d

infra-down: ## Stop Docker Compose services
	docker compose down

# ── Development ─────────────────────────────────────────────────────────────

backend-dev: ## Run FastAPI backend in development mode
	cd $(BACKEND_DIR) && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend-dev: ## Run Next.js frontend in development mode
	cd $(FRONTEND_DIR) && npm run dev

# ── Database ────────────────────────────────────────────────────────────────

db-migrate: ## Apply pending database migrations
	cd $(BACKEND_DIR) && alembic upgrade head

db-revision: ## Create a new migration revision (usage: make db-revision MSG="add users table")
	cd $(BACKEND_DIR) && alembic revision --autogenerate -m "$(MSG)"

# ── Testing ─────────────────────────────────────────────────────────────────

test: test-unit test-integration ## Run all tests

test-unit: ## Run unit tests
	cd $(BACKEND_DIR) && python -m pytest tests/unit -v --tb=short

test-integration: ## Run integration tests (requires Docker services)
	cd $(BACKEND_DIR) && python -m pytest tests/integration -v --tb=short

# ── Code Quality ────────────────────────────────────────────────────────────

lint: ## Run all linters
	cd $(BACKEND_DIR) && ruff check .
	cd $(BACKEND_DIR) && mypy .
	cd $(FRONTEND_DIR) && npx next lint
	cd $(FRONTEND_DIR) && npx prettier --check .

format: ## Auto-format all code
	cd $(BACKEND_DIR) && ruff format .
	cd $(BACKEND_DIR) && ruff check --fix .
	cd $(FRONTEND_DIR) && npx prettier --write .
	cd $(FRONTEND_DIR) && npx next lint --fix

typecheck: ## Run type checkers (mypy + tsc)
	cd $(BACKEND_DIR) && mypy .
	cd $(FRONTEND_DIR) && npx tsc --noEmit

# ── Contracts ───────────────────────────────────────────────────────────────

contracts-validate: ## Validate OpenAPI and AsyncAPI specs
	npx @redocly/cli lint $(CONTRACTS_DIR)/openapi.yaml
	npx @asyncapi/cli validate $(CONTRACTS_DIR)/asyncapi.yaml

generate-client: ## Generate TypeScript client from OpenAPI spec
	./scripts/generate-client.sh

# ── Cleanup ─────────────────────────────────────────────────────────────────

clean: ## Remove build artifacts, caches, and virtual environments
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf $(FRONTEND_DIR)/.next $(FRONTEND_DIR)/node_modules/.cache
	rm -rf $(BACKEND_DIR)/htmlcov $(BACKEND_DIR)/.coverage
	rm -rf dist build *.egg-info
