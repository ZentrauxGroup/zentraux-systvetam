# SYSTVETAM — Developer Commands
# Zentraux Group LLC
#
# Usage: make <target>
# Run from project root (systvetam/)

COMPOSE := docker compose -f infra/docker-compose.yml --env-file infra/.env
DISPATCH_CONTAINER := systvetam-dispatch

.PHONY: help up down logs migrate revision seed shell health test clean status fmt

# ---------------------------------------------------------------------------
# Default target
# ---------------------------------------------------------------------------

help: ## Show available commands
	@echo ""
	@echo "  SYSTVETAM — Developer Commands"
	@echo "  =============================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ---------------------------------------------------------------------------
# Docker Compose lifecycle
# ---------------------------------------------------------------------------

up: ## Start all services (detached)
	$(COMPOSE) up -d
	@echo ""
	@echo "  Systvetam is up."
	@echo "  Dispatch:  http://localhost:8000"
	@echo "  Dashboard: http://localhost:3000"
	@echo "  Docs:      http://localhost:8000/docs"
	@echo ""

down: ## Stop all services
	$(COMPOSE) down

logs: ## Tail dispatch logs (follow)
	$(COMPOSE) logs -f dispatch

logs-all: ## Tail all service logs
	$(COMPOSE) logs -f

clean: ## Stop + destroy volumes (nuclear — deletes DB data)
	@echo "WARNING: This destroys all data volumes."
	@read -p "Type 'yes' to confirm: " confirm && [ "$$confirm" = "yes" ] || exit 1
	$(COMPOSE) down -v

restart: ## Restart dispatch only
	$(COMPOSE) restart dispatch

rebuild: ## Rebuild dispatch image and restart
	$(COMPOSE) up -d --build dispatch

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

migrate: ## Run alembic migrations (upgrade head)
	$(COMPOSE) exec dispatch alembic upgrade head

revision: ## Generate new alembic migration (autogenerate)
	@read -p "Migration message: " msg && \
	$(COMPOSE) exec dispatch alembic revision --autogenerate -m "$$msg"

seed: ## Seed crew members from canonical role files
	$(COMPOSE) exec dispatch python -m scripts.seed_crew

dbshell: ## Open psql shell in postgres container
	$(COMPOSE) exec postgres psql -U zos -d systvetam

# ---------------------------------------------------------------------------
# Development
# ---------------------------------------------------------------------------

shell: ## Open bash shell in dispatch container
	docker exec -it $(DISPATCH_CONTAINER) bash

health: ## Hit the health endpoint
	@curl -s http://localhost:8000/health | python3 -m json.tool

status: ## Hit the full status endpoint
	@curl -s http://localhost:8000/status | python3 -m json.tool

test: ## Run pytest suite
	$(COMPOSE) exec dispatch pytest tests/ -v --tb=short

# ---------------------------------------------------------------------------
# Quick checks
# ---------------------------------------------------------------------------

ps: ## Show running containers
	$(COMPOSE) ps

fmt: ## Format Python code (black + isort)
	$(COMPOSE) exec dispatch black dispatch/ --line-length 100
	$(COMPOSE) exec dispatch isort dispatch/ --profile black
