# Phase 0 — Foundations

**Goal:** Runnable monorepo: `docker compose up` brings up API, web, Postgres, Redis, and Caddy; demo users for all four roles can log in; lint/type/test pass.

**Out of scope:** Catalog, recipes, ledger, POS, scanner, reports.

## Files / areas

| Area | Path |
|---|---|
| Arabic requirements | `docs/requirements-ar.md` |
| Decisions | `docs/decisions.md` |
| Backend app | `backend/app/` |
| Migrations | `backend/alembic/` |
| Tests | `backend/tests/` |
| Frontend | `frontend/src/` |
| Compose | `docker-compose.yml`, `caddy/Caddyfile` |

## Models (Phase 0 only)

`branches`, `locations`, `users`, `roles`, `permissions`, `role_permissions`, `user_roles`, `audit_logs`, `settings`

## Endpoints

- `GET /api/v1/health`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `GET /api/v1/auth/me`

## Seed

- 1 branch, 3 locations (fridge, dry storage, prep)
- Single `OPERATOR` role with full permissions (home one-person shop)
- 1 demo user (password in README)
- Settings: `negative_stock_policy=WARN`, `tax_rate=0`

## Acceptance

- [ ] `docker compose up` works
- [ ] Login works for all seeded roles
- [ ] Cashier lacks `products.edit`, `recipes.edit`, `reports.view_profit`
- [ ] Backend tests on real Postgres
- [ ] Ruff, mypy, ESLint, `tsc` clean
- [ ] Phase 1 not started
