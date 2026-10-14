# Phase 1 — Catalog & Units

**Goal:** Units/conversions, ingredients, suppliers, categories, products, variants, versioned recipes, modifiers, live cost. Seed demo catalog.

**Accept:** tests 4, 8 (cost), 11; operator can create Chicken Wrap via API/UI data-only.

## Deliverables

- Models + Alembic migration `0002_phase1_catalog`
- `UnitConversionService`, `RecipeService`, `CostingService`
- APIs under `/api/v1` for catalog CRUD + recipe versions
- Seed catalog from requirements
- Frontend: ingredients list, products list/editor with recipe + live cost
- Decision D-010: single operator (no cashier 403 tests)

## Tests

- Latte S vs L milk qty in base ml
- Recipe versioning: new version does not mutate old
- Unit convert kg→g; reject g→ml without density
