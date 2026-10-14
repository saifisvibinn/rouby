.PHONY: up down migrate seed test lint typecheck logs

up:
	docker compose up --build

down:
	docker compose down

migrate:
	cd backend && uv run alembic upgrade head

seed:
	cd backend && uv run python -m app.cli seed

test:
	cd backend && uv run pytest -v
	cd frontend && npm test -- --run

lint:
	cd backend && uv run ruff check .
	cd frontend && npm run lint

typecheck:
	cd backend && uv run mypy app
	cd frontend && npm run typecheck

logs:
	docker compose logs -f
