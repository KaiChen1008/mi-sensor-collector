BACKEND_DIR  := backend
FRONTEND_DIR := frontend

.DEFAULT_GOAL := help
.PHONY: help install \
        dev dev-sim dev-homekit dev-full \
        backend backend-sim frontend homekit \
        test test-v test-file \
        lint lint-fix format check \
        build docker-up docker-down docker-homekit docker-build \
        clean clean-db clean-frontend clean-all

# ── Help ────────────────────────────────────────────────────────────────────────
help:
	@printf "\n\033[1mMi Sensor Collector\033[0m\n\n"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@printf "\n"

# ── Setup ───────────────────────────────────────────────────────────────────────
install: ## Install all backend and frontend dependencies
	cd $(BACKEND_DIR) && uv sync
	npm install --prefix $(FRONTEND_DIR)

# ── Development (all-in-one) ────────────────────────────────────────────────────
dev: ## Start backend + frontend (real BLE sensors)
	./start-dev.sh

dev-sim: ## Start backend + frontend with simulated sensor data
	SIMULATE=true ./start-dev.sh

dev-homekit: ## Start backend + frontend + HomeKit bridge
	HOMEKIT=true ./start-dev.sh

dev-full: ## Start everything with simulated data + HomeKit bridge
	SIMULATE=true HOMEKIT=true ./start-dev.sh

# ── Individual services ──────────────────────────────────────────────────────────
backend: ## Run backend only (real BLE)
	cd $(BACKEND_DIR) && uv run python run.py

backend-sim: ## Run backend only with simulated data
	cd $(BACKEND_DIR) && SIMULATE_SENSORS=true uv run python run.py

frontend: ## Run frontend dev server only
	npm run dev --prefix $(FRONTEND_DIR)

homekit: ## Run HomeKit bridge only (backend must be running)
	cd $(BACKEND_DIR) && uv run python -m app.services.homekit_bridge

# ── Testing ──────────────────────────────────────────────────────────────────────
test: ## Run all 93 tests
	cd $(BACKEND_DIR) && uv run pytest

test-v: ## Run all tests (verbose)
	cd $(BACKEND_DIR) && uv run pytest -v

test-file: ## Run a single test file  →  make test-file FILE=tests/test_api_sensors.py
	cd $(BACKEND_DIR) && uv run pytest $(FILE)

# ── Lint & Format ────────────────────────────────────────────────────────────────
format: ## Auto-format all backend Python files with ruff
	cd $(BACKEND_DIR) && uv run ruff format .

lint: ## Lint backend Python files with ruff
	cd $(BACKEND_DIR) && uv run ruff check .

lint-fix: ## Lint and auto-fix backend Python files
	cd $(BACKEND_DIR) && uv run ruff check --fix .

check: format lint test ## Format + lint + test (run before committing)

# ── Build ────────────────────────────────────────────────────────────────────────
build: ## Build frontend for production (output → frontend/dist/)
	npm run build --prefix $(FRONTEND_DIR)

# ── Docker ───────────────────────────────────────────────────────────────────────
docker-up: ## Start backend + frontend via Docker Compose
	docker compose up

docker-down: ## Stop and remove Docker Compose containers
	docker compose down

docker-homekit: ## Start all services including HomeKit bridge via Docker
	docker compose --profile homekit up

docker-build: ## Rebuild Docker images
	docker compose build

# ── Clean ────────────────────────────────────────────────────────────────────────
clean: ## Remove Python cache, test artifacts, and coverage files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -o -name "*.pyo" | xargs rm -f 2>/dev/null || true
	rm -rf $(BACKEND_DIR)/.pytest_cache
	rm -rf $(BACKEND_DIR)/.ruff_cache
	rm -rf $(BACKEND_DIR)/.mypy_cache
	rm -rf $(BACKEND_DIR)/htmlcov
	rm -f  $(BACKEND_DIR)/.coverage
	@printf "\033[32mPython cache cleaned.\033[0m\n"

clean-db: ## Delete the SQLite database (recreated on next startup)
	rm -f $(BACKEND_DIR)/data/sensors.db
	@printf "\033[33mDatabase deleted — will be recreated on next startup.\033[0m\n"

clean-frontend: ## Remove frontend build output
	rm -rf $(FRONTEND_DIR)/dist
	@printf "\033[32mFrontend build artifacts removed.\033[0m\n"

clean-all: clean clean-db clean-frontend ## Remove everything including node_modules
	rm -rf $(FRONTEND_DIR)/node_modules
	@printf "\033[32mFull clean complete.\033[0m\n"
