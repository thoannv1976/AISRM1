# AISRM1 — developer convenience targets
.PHONY: help up down logs api web worker migrate seed test lint fmt install

help:
	@echo "AISRM1 — AI-ResearchHub"
	@echo "  make up        - start full stack (docker compose)"
	@echo "  make down      - stop stack"
	@echo "  make logs      - tail logs"
	@echo "  make migrate   - run DB migrations (api container)"
	@echo "  make seed      - load demo seed data"
	@echo "  make test      - run backend tests"
	@echo "  make lint      - lint backend"
	@echo "  make fmt       - format backend"

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f --tail=120

migrate:
	docker compose exec api python -m app.cli migrate

seed:
	docker compose exec api python -m app.cli seed --demo

test:
	cd apps/api && pytest -q

lint:
	cd apps/api && ruff check app && ruff format --check app

fmt:
	cd apps/api && ruff format app && ruff check --fix app

install:
	cd apps/api && pip install -e ".[dev]"
	cd apps/web && npm install
