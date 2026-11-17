VENV ?= .venv
PYTHON = $(if $(wildcard $(VENV)/bin/python),$(VENV)/bin/python,python3)
RUFF = $(if $(wildcard $(VENV)/bin/ruff),$(VENV)/bin/ruff,ruff)
PYTEST = $(if $(wildcard $(VENV)/bin/pytest),$(VENV)/bin/pytest,pytest)
ALEMBIC = $(if $(wildcard $(VENV)/bin/alembic),$(VENV)/bin/alembic,alembic)

.PHONY: help setup install lint test test-backend test-frontend dev clean docker-up docker-down migrate seed

help:
	@echo "Kexpense Monorepo Management"
	@echo "Available commands:"
	@echo "  make setup       - Full environment setup (deps & env)"
	@echo "  make install     - Install dependencies for backend & frontend"
	@echo "  make docker-up   - Start local PostgreSQL database container"
	@echo "  make docker-down - Stop local PostgreSQL database container"
	@echo "  make migrate     - Run database migrations (Alembic upgrade head)"
	@echo "  make seed        - Seed default Vietnamese system categories & rules"
	@echo "  make dev         - Instructions to start local development services"
	@echo "  make lint        - Run linting and code formatting checks"
	@echo "  make test        - Run backend and frontend test suite"
	@echo "  make clean       - Clean temporary build caches"

setup:
	@if [ ! -f .env ]; then cp .env.example .env; echo "[+] Created .env from .env.example"; fi
	@if [ ! -f backend/.env ]; then cp backend/.env.example backend/.env; echo "[+] Created backend/.env"; fi
	@if [ ! -f frontend/.env ]; then cp frontend/.env.example frontend/.env; echo "[+] Created frontend/.env"; fi
	@echo "[+] Environment setup ready."

docker-up:
	docker compose up -d --wait postgres

docker-down:
	docker compose down

install:
	pip install -r backend/requirements-dev.txt
	cd frontend && npm install

migrate:
	cd backend && ../$(ALEMBIC) upgrade head

seed:
	$(PYTHON) -m backend.app.core.seed_categories

lint:
	cd backend && ../$(RUFF) check . && ../$(RUFF) format --check .
	cd frontend && npm run lint && npm run type-check

test-backend:
	PYTHONPATH=. $(PYTEST) -v

test-frontend:
	cd frontend && npm run test

test: test-backend test-frontend
	$(PYTHON) -m scripts.validate_dataset --manifest data/manifest.csv

dev:
	@echo "To start Backend:  uvicorn backend.app.main:app --reload --port 8000"
	@echo "To start Frontend: cd frontend && npm run dev"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	rm -rf frontend/.next frontend/dist
