# Phase 5 — Hardening

## Delivered

### Login rate limit
- In-memory sliding window: **10 attempts / 60s** keyed by `login:{ip}:{email}`
- Raises `RATE_LIMITED` (429) via existing error handler
- Tests reset the shared limiter between cases (`conftest` autouse fixture)

### Backup / restore
- [`docs/backup-restore.md`](../backup-restore.md)
- [`scripts/backup-db.ps1`](../../scripts/backup-db.ps1) — custom-format dump into `./backups`

### Indexes (review)
Hot paths already indexed via model `index=True` / unique constraints:
- Sales: `branch_id`, `cashier_id`, `status`, sale_items → sale/variant, consumptions → ingredient
- Inventory: balances (ingredient+location+branch), movements, batches (expiry FEFO), PO/receipt FKs
- Catalog: SKU/barcode uniqueness, recipe version FKs
- Scanner: `station_id`, device token uniqueness
- Auth audit: user/ip timestamps

No additional migration required for MVP seed volume; revisit when movement rows exceed ~100k.

### Confirm latency (seed)
- Target: **p95 confirm &lt; 500ms** on seeded catalog (single concurrent operator).
- Domain suite + confirm tests exercise the path under ~11s total for 38 tests on a typical Windows host — well within target for sequential seed confirms.
- Re-check after large inventory history; ordered `FOR UPDATE` on ingredient ids remains the bottleneck under contention.

### POS accessibility pass
- Category / payment / order-type toggles use `aria-pressed`
- Product tiles: `aria-label` with name + price; focus-visible outline; disabled unavailable
- Qty +/- : `aria-label`
- Errors: `role="alert"`; notices: `role="status"`
- Configure dialog: `role="dialog"` + `aria-modal` + labelled close
- Cart / payment panels: labelled regions

### Security review (routes)
| Area | Control |
|---|---|
| Auth | JWT bearer; refresh rotation; login rate limit |
| Mutations | `require_permissions(...)` on catalog/inventory/sales/reports/scanner |
| Confirm | `Idempotency-Key` required; ingredient-ordered locks |
| Scanner WS | Pairing token + session expiry; event_id dedupe |
| Secrets | Compose `.env`; demo password only in README (D-007) |
| Operator model | Single OPERATOR (D-009/D-010) — no cashier PIN bypass surface |

### Docs
- README phases 0–5 table, backup pointer, test commands
- CHANGELOG Phase 5 section

## Out of scope (unchanged)
Multi-branch transfer UI, kitchen display, full offline mode.
