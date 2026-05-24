# ============================
# WOLLOYEWA STORE BOT - MAKEFILE
# ============================
# Usage: make <command>
# Example: make install, make dev, make test

.PHONY: help install install-dev clean dev test test-cov lint format typecheck security migrate backup docker-up docker-down docker-build deploy

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

# Default target
help:
	@echo "$(GREEN)Wolloyewa Store Bot - Makefile Commands$(NC)"
	@echo "$(YELLOW)Setup & Installation:$(NC)"
	@echo "  make install      - Install production dependencies"
	@echo "  make install-dev  - Install development dependencies"
	@echo "  make clean        - Clean Python cache files"
	@echo ""
	@echo "$(YELLOW)Development:$(NC)"
	@echo "  make dev          - Run development server"
	@echo "  make test         - Run tests"
	@echo "  make test-cov     - Run tests with coverage"
	@echo "  make lint         - Run linters"
	@echo "  make format       - Format code"
	@echo "  make typecheck    - Run type checking"
	@echo "  make security     - Run security checks"
	@echo ""
	@echo "$(YELLOW)Database:$(NC)"
	@echo "  make migrate      - Run database migrations"
	@echo "  make makemigrations - Create new migration"
	@echo "  make downgrade    - Rollback last migration"
	@echo "  make seed         - Seed database with dummy data"
	@echo ""
	@echo "$(YELLOW)Docker:$(NC)"
	@echo "  make docker-up    - Start all containers"
	@echo "  make docker-down  - Stop all containers"
	@echo "  make docker-build - Build Docker images"
	@echo "  make docker-logs  - View container logs"
	@echo ""
	@echo "$(YELLOW)Utilities:$(NC)"
	@echo "  make backup       - Backup database"
	@echo "  make restore      - Restore database"
	@echo "  make deploy       - Deploy to production"
	@echo "  make monitor      - Run monitoring checks"

# ============================
# Setup & Installation
# ============================

install:
	@echo "$(GREEN)Installing production dependencies...$(NC)"
	pip install --upgrade pip
	pip install -r requirements.txt
	@echo "$(GREEN)Installation complete!$(NC)"

install-dev:
	@echo "$(GREEN)Installing development dependencies...$(NC)"
	pip install --upgrade pip
	pip install -r requirements-dev.txt
	pre-commit install
	@echo "$(GREEN)Installation complete!$(NC)"

clean:
	@echo "$(YELLOW)Cleaning Python cache files...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.so" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)Clean complete!$(NC)"

# ============================
# Development
# ============================

dev:
	@echo "$(GREEN)Starting development server...$(NC)"
	uvicorn main:app --reload --host 0.0.0.0 --port 8000 --log-level debug

test:
	@echo "$(GREEN)Running tests...$(NC)"
	pytest -v

test-cov:
	@echo "$(GREEN)Running tests with coverage...$(NC)"
	pytest --cov=. --cov-report=html --cov-report=term-missing
	@echo "$(GREEN)Coverage report generated in htmlcov/index.html$(NC)"

test-integration:
	@echo "$(GREEN)Running integration tests...$(NC)"
	pytest -v -m integration

test-unit:
	@echo "$(GREEN)Running unit tests...$(NC)"
	pytest -v -m unit

lint:
	@echo "$(GREEN)Running linters...$(NC)"
	ruff check .
	flake8 .
	@echo "$(GREEN)Linting complete!$(NC)"

format:
	@echo "$(GREEN)Formatting code...$(NC)"
	black .
	isort .
	@echo "$(GREEN)Formatting complete!$(NC)"

typecheck:
	@echo "$(GREEN)Running type checker...$(NC)"
	mypy .
	@echo "$(GREEN)Type checking complete!$(NC)"

security:
	@echo "$(GREEN)Running security checks...$(NC)"
	bandit -r . -c pyproject.toml
	safety check
	@echo "$(GREEN)Security checks complete!$(NC)"

all-checks: format lint typecheck test security
	@echo "$(GREEN)All checks passed!$(NC)"

# ============================
# Database
# ============================

migrate:
	@echo "$(GREEN)Running database migrations...$(NC)"
	alembic upgrade head
	@echo "$(GREEN)Migrations complete!$(NC)"

makemigrations:
	@echo "$(GREEN)Creating new migration...$(NC)"
	@read -p "Enter migration message: " msg; \
	alembic revision --autogenerate -m "$$msg"
	@echo "$(GREEN)Migration created!$(NC)"

downgrade:
	@echo "$(YELLOW)Rolling back last migration...$(NC)"
	alembic downgrade -1
	@echo "$(GREEN)Rollback complete!$(NC)"

seed:
	@echo "$(GREEN)Seeding database...$(NC)"
	python scripts/seed_db.py
	@echo "$(GREEN)Database seeded!$(NC)"

reset-db: clean-db migrate seed
	@echo "$(GREEN)Database reset complete!$(NC)"

clean-db:
	@echo "$(RED)WARNING: This will delete all data!$(NC)"
	@read -p "Are you sure? (y/N): " confirm; \
	if [ "$$confirm" = "y" ]; then \
		alembic downgrade base; \
		echo "$(GREEN)Database cleaned!$(NC)"; \
	else \
		echo "$(YELLOW)Cancelled$(NC)"; \
	fi

# ============================
# Docker Commands
# ============================

docker-up:
	@echo "$(GREEN)Starting Docker containers...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)Containers started!$(NC)"
	@echo "Access services:"
	@echo "  API: http://localhost:8000"
	@echo "  PGAdmin: http://localhost:5050"
	@echo "  Flower: http://localhost:5555"
	@echo "  Prometheus: http://localhost:9090"
	@echo "  Grafana: http://localhost:3000"

docker-down:
	@echo "$(YELLOW)Stopping Docker containers...$(NC)"
	docker-compose down
	@echo "$(GREEN)Containers stopped!$(NC)"

docker-down-volumes:
	@echo "$(RED)WARNING: This will delete all volumes!$(NC)"
	@read -p "Are you sure? (y/N): " confirm; \
	if [ "$$confirm" = "y" ]; then \
		docker-compose down -v; \
		echo "$(GREEN)Volumes deleted!$(NC)"; \
	else \
		echo "$(YELLOW)Cancelled$(NC)"; \
	fi

docker-build:
	@echo "$(GREEN)Building Docker images...$(NC)"
	docker-compose build --no-cache
	@echo "$(GREEN)Build complete!$(NC)"

docker-logs:
	@echo "$(GREEN)Showing logs...$(NC)"
	docker-compose logs -f

docker-logs-app:
	@echo "$(GREEN)Showing app logs...$(NC)"
	docker-compose logs -f app

docker-logs-worker:
	@echo "$(GREEN)Showing worker logs...$(NC)"
	docker-compose logs -f celery_worker

docker-shell:
	@echo "$(GREEN)Opening shell in app container...$(NC)"
	docker-compose exec app bash

docker-db-shell:
	@echo "$(GREEN)Opening PostgreSQL shell...$(NC)"
	docker-compose exec postgres psql -U postgres -d welloyewadb

# ============================
# Production Deployment
# ============================

deploy:
	@echo "$(YELLOW)Deploying to production...$(NC)"
	@echo "This will deploy to production server"
	@read -p "Continue? (y/N): " confirm; \
	if [ "$$confirm" = "y" ]; then \
		./scripts/deploy.sh; \
	else \
		echo "$(YELLOW)Deployment cancelled$(NC)"; \
	fi

deploy-staging:
	@echo "$(YELLOW)Deploying to staging...$(NC)"
	./scripts/deploy.sh staging

# ============================
# Backup & Restore
# ============================

backup:
	@echo "$(GREEN)Creating database backup...$(NC)"
	./scripts/backup.sh
	@echo "$(GREEN)Backup complete!$(NC)"

restore:
	@echo "$(YELLOW)Restoring database...$(NC)"
	@read -p "Enter backup filename: " filename; \
	./scripts/restore.sh $$filename
	@echo "$(GREEN)Restore complete!$(NC)"

# ============================
# Monitoring
# ============================

monitor:
	@echo "$(GREEN)Running health checks...$(NC)"
	./scripts/healthcheck.sh
	@echo "$(GREEN)Health check complete!$(NC)"

monitor-prometheus:
	@echo "$(GREEN)Checking Prometheus targets...$(NC)"
	curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[].health'

# ============================
# Utilities
# ============================

shell:
	@echo "$(GREEN)Opening Python shell...$(NC)"
	ipython

env:
	@echo "$(GREEN)Showing environment variables...$(NC)"
	cat .env | grep -v "^#" | grep -v "^$$"

update-deps:
	@echo "$(GREEN)Updating dependencies...$(NC)"
	pip install --upgrade pip-tools
	pip-compile --upgrade requirements.in
	pip-compile --upgrade requirements-dev.in
	@echo "$(GREEN)Dependencies updated!$(NC)"

sync-deps:
	@echo "$(GREEN)Syncing dependencies...$(NC)"
	pip-sync requirements.txt requirements-dev.txt

# ============================
# Documentation
# ============================

docs:
	@echo "$(GREEN)Building documentation...$(NC)"
	mkdocs build
	@echo "$(GREEN)Documentation built in site/$(NC)"

docs-serve:
	@echo "$(GREEN)Serving documentation...$(NC)"
	mkdocs serve

# ============================
# Git Hooks
# ============================

pre-commit:
	@echo "$(GREEN)Running pre-commit hooks...$(NC)"
	pre-commit run --all-files
	@echo "$(GREEN)Pre-commit checks complete!$(NC)"

# ============================
# Quick Commands
# ============================

all: install-dev pre-commit all-checks
	@echo "$(GREEN)All tasks completed successfully!$(NC)"

ci: clean install-dev lint typecheck test security
	@echo "$(GREEN)CI checks passed!$(NC)"

.PHONY: help install install-dev clean dev test test-cov lint format typecheck security migrate makemigrations downgrade seed docker-up docker-down docker-build deploy backup restore monitor