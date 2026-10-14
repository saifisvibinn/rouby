# Changelog

## [Unreleased]

### Back-office UI

- Products (variants + recipe editor/history/cost), Ingredients (stock badges), Inventory (balances/ledger/waste/counts), Purchasing (PO + goods receipt), Settings
- Catalog list APIs: categories, suppliers, recipe cost; locations + settings endpoints

### Phase 5 — Hardening

- Login rate limiting (10 attempts / minute / IP+email); limiter reset between pytest cases
- Backup/restore docs + `scripts/backup-db.ps1`
- Index review, confirm latency note, POS a11y pass, route security checklist
- Final docs for phases 1–5

### Phase 4 — Reports & Dashboard

- Sales, inventory, profit, usage-variance, reorder-suggestion reports + CSV
- Dashboard KPIs (today sales, orders, avg ticket, gross profit, low stock)

### Phase 3B — Phone Scanner

- Scanner pairing sessions, resolve API, WebSockets + Redis pub/sub
- `/scanner` mobile page; `docs/scanner-setup.md`

### Phase 3 — POS & Orders

- Sales lifecycle, confirm with Idempotency-Key + stock deduction + COGS snapshot
- Split payments, cancel/reversal/waste, POS menu, frontend POS + Playwright flow

### Phase 2 — Inventory Core

- Ledger `stock_movements`, balances, FEFO batches, WAC on goods receipt
- Waste, stock counts, PO→receipt (PO does not change stock)

### Phase 1 — Catalog & Units

- Units/conversions, ingredients, products, variants, versioned recipes, modifiers
- Live theoretical cost; seed Healthy Food & Coffee demo catalog

### Phase 0 — Foundations

- FastAPI + React/Vite + Docker Compose (api, web, db, redis, caddy)
- JWT auth, single OPERATOR user (`admin` / `admin`)
- Arabic requirements at `docs/requirements-ar.md`
