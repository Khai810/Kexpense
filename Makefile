.PHONY: help install lint test dev clean

help:
	@echo "Available commands:"
	@echo "  make install     - Install dependencies for backend & frontend"
	@echo "  make dev         - Run development servers"
	@echo "  make lint        - Run linting checks (ruff & eslint)"
	@echo "  make test        - Run automated tests"
	@echo "  make clean       - Clean temporary and build files"

lint:
	cd backend && ruff check . && ruff format --check .
	cd frontend && pnpm lint

test:
	cd backend && pytest tests/ -v
	cd frontend && pnpm test
