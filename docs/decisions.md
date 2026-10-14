# Decisions

## Phase 0

| ID | Decision | Rationale |
|---|---|---|
| D-001 | Default UI language is English; Arabic + RTL togglable | Safer scaffolding; restaurant can switch |
| D-002 | Negative stock policy default `WARN` | Spec default; BLOCK available via settings later |
| D-003 | Tax rate seeded as `0` | Restaurant configures later; avoids inventing Egypt VAT |
| D-004 | ~~Multi-role staff RBAC~~ → **superseded by D-009** | Home restaurant is one-person |
| D-005 | Redis and Caddy in Compose from Phase 0; API does not require Redis yet | Avoid rework for Phase 3B scanner WebSockets / HTTPS |
| D-006 | English technical prompt wins over Arabic requirements on conflicts | Binding hierarchy in project prompt |
| D-007 | Demo passwords documented in README only (dev) | Seed requirement; never for production |
| D-008 | Demo emails use `@rouby.app` (not `.local`) | Pydantic EmailStr rejects reserved TLDs like `.local` |
| D-009 | Single `OPERATOR` role + one demo user; no staff roles / Users UI | Home-run one-person shop; permission tables kept for future only |

## Phase 3

| ID | Decision | Rationale |
|---|---|---|
| D-010 | Single operator replaces cashier 403 test; no separate cashier role | Same user creates and confirms sales; permission `sales.create` covers all POS actions |
