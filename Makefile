.PHONY: help dev dev-backend dev-frontend build test test-backend test-frontend clean docker docker-up docker-down docker-build

# Default target
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Development ─────────────────────────────────────────────────────

dev: dev-backend dev-frontend ## Run backend and frontend in dev mode (parallel)

dev-backend: ## Run backend (uvicorn with reload)
	cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000

dev-frontend: ## Run frontend (Vite dev server)
	cd frontend && npm run dev

# ── Install ─────────────────────────────────────────────────────────

install: install-backend install-frontend ## Install all dependencies

install-backend: ## Install backend dependencies
	cd backend && python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"

install-frontend: ## Install frontend dependencies
	cd frontend && npm install

# ── Config ───────────────────────────────────────────────────────────

config: ## Create config.json if it doesn't exist
	@test -f frontend/public/config.json || echo '{}' > frontend/public/config.json

# ── Build ───────────────────────────────────────────────────────────

build: build-frontend ## Build everything

build-frontend: ## Build frontend (output: backend/app/static/)
	cd frontend && npm run build

# ── Test ────────────────────────────────────────────────────────────

test: test-backend test-frontend ## Run all tests

test-backend: ## Run backend tests
	cd backend && source .venv/bin/activate && pytest

test-frontend: ## Run frontend tests
	cd frontend && npm test

test-watch: ## Run frontend tests in watch mode
	cd frontend && npm run test:watch

# ── Docker ──────────────────────────────────────────────────────────

docker: docker-up ## Alias for docker-up

docker-up: config ## Start Docker containers
	docker compose up -d

docker-down: ## Stop Docker containers
	docker compose down

docker-build: ## Build Docker image
	docker compose build

docker-logs: ## Show Docker logs
	docker compose logs -f

# ── Split deployment ────────────────────────────────────────────────

deploy-frontend: build-frontend ## Build and start frontend container
	docker compose -f docker-compose.frontend.yml up -d

deploy-backend: ## Start backend container
	docker compose -f docker-compose.backend.yml up -d

# ── Clean ───────────────────────────────────────────────────────────

clean: ## Clean build artifacts and caches
	cd frontend && rm -rf dist node_modules
	cd backend && rm -rf __pycache__ .pytest_cache *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true

clean-data: ## Clean all data (uploads, output, jobs) ⚠️ DESTRUCTIVE
	rm -rf data/uploads/* data/output/* data/jobs/*

# ── Lint ────────────────────────────────────────────────────────────

lint-backend: ## Run backend linter (if configured)
	cd backend && source .venv/bin/activate && python -m py_compile app/main.py

lint-frontend: ## Run frontend type check
	cd frontend && npm run type-check 2>/dev/null || echo "type-check not configured"
