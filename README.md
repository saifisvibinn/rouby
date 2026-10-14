# Rouby — Restaurant POS + Smart Inventory

Single-branch **Healthy Food & Coffee** POS + smart inventory (Egypt, EGP). Every sold product is a **Recipe** that consumes **Ingredients** — never just a name and a price.

**Stack:** FastAPI + PostgreSQL 16 + SQLAlchemy 2 async + Alembic · React + TypeScript + Vite + Tailwind · Docker Compose (api, web, db, redis, caddy)

## Quick start

```powershell
cd C:\Users\drago\Desktop\Rouby
cp .env.example .env   # if needed
docker compose up --build
```

- App: http://localhost:5173
- API docs: http://localhost:8000/docs
- Scanner pairing: use **Connect phone scanner** on POS (see [`docs/scanner-setup.md`](docs/scanner-setup.md))

### Demo login

| Username | Password |
|---|---|
| admin | admin |

## Deploy (free)

1. **Frontend (Vercel):** import the GitHub repo, set root to `frontend`, add env `VITE_API_URL` = your API URL.
2. **API + Postgres (Render):** use [`render.yaml`](render.yaml) Blueprint, then set `CORS_ORIGINS` to your Vercel URL (comma-separated).
3. After the API is live, rebuild the Vercel project so `VITE_API_URL` is baked into the client.

### Local API (Compose for db/redis only)

```powershell
docker compose up -d db redis
cd backend
uv sync
uv run alembic upgrade head
uv run python -m app.cli seed
uv run uvicorn app.main:app --reload --port 8000
```

```powershell
cd frontend
npm install
npm run dev
```

## What shipped (Phases 0–5)

| Phase | Capability |
|---|---|
| 0 | Auth, Docker, i18n/RTL shell |
| 1 | Units, ingredients, products, recipes, modifiers, live cost |
| 2 | Ledger inventory, WAC, PO→receipt, waste, counts, FEFO |
| 3 | POS, confirm+idempotency+deduction, payments, cancel |
| 3B | Phone scanner pairing, resolve, WebSockets |
| 4 | Dashboard + sales/inventory/profit reports |
| 5 | Login rate limit, backup script/docs, indexes/a11y/security notes |
| UI | Full back-office: products, ingredients, inventory, purchasing, settings |

## Tests

```powershell
cd backend
uv run pytest -q

cd ..\frontend
npm test -- --run
npm run typecheck
npm run test:e2e -- --project=chromium
```

## Backup

See [`docs/backup-restore.md`](docs/backup-restore.md) and `scripts/backup-db.ps1`.

## Docs

- Arabic requirements: [`docs/requirements-ar.md`](docs/requirements-ar.md)
- Plans: [`docs/plan/`](docs/plan/)
- Decisions: [`docs/decisions.md`](docs/decisions.md)
- Changelog: [`docs/CHANGELOG.md`](docs/CHANGELOG.md)
- Scanner HTTPS: [`docs/scanner-setup.md`](docs/scanner-setup.md)
