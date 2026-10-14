---
name: pos-inventory-domain
description: Business invariants for the restaurant POS and inventory system. Use whenever touching sales, recipes, modifiers, stock movements, purchasing, costing, units, or reports.
---

# POS + Inventory Domain Invariants

Re-read this checklist **before** any change that touches sales, recipes, modifiers, stock movements, purchasing, costing, units, or reports. Do not ship code that violates these rules.

## Checklist

- [ ] **Products ≠ Ingredients.** Sold catalog items are not stocked as products. Every sold item is a **variant** with a **versioned recipe** of ingredients.
- [ ] **Base units only.** All stock math uses ingredient base units (`g` / `ml` / `count`). Never convert across dimensions without an explicit density (or equivalent) factor.
- [ ] **Decimal only.** Money and quantities use `Decimal` (or DB numeric) — **never** floats.
- [ ] **`stock_movements` is source of truth.** The ledger is append-only. Balances update in the **same transaction** as the movement. Corrections are **reversing movements**, never edits or deletes of past rows.
- [ ] **Deduct exactly once at CONFIRMED.** Stock deduction happens only when an order reaches `CONFIRMED`, inside **one transaction**, with an `Idempotency-Key`, locking ingredients via `SELECT … FOR UPDATE` in **ingredient-id order** (deadlock-safe).
- [ ] **Effective recipe drives deduct + cost.** Effective recipe = variant recipe + modifier effects (`ADD` / `REMOVE` / `REPLACE` / `MULTIPLY`). Deduct stock and compute cost from the effective recipe, not the bare variant alone.
- [ ] **Cost snapshot per sale line.** Store cost on the sale line at confirm time. Historical COGS is **never** recalculated from later recipe or WAC changes.
- [ ] **POs do not touch stock.** Purchase orders are commitments only. Only a **confirmed goods receipt** creates stock movements and updates **WAC**.
- [ ] **FEFO allocation.** Batch picks allocate First-Expired-First-Out.
- [ ] **Cancellation rules.** Before `PREPARING` → automatic stock **reversal**. After `PREPARING` → manager chooses **return-to-stock** or **waste**; either path requires an **audit log** entry.
- [ ] **Audit every sensitive action.** Confirm, cancel, void, waste, receipt, WAC adjust, recipe publish, permission overrides — each writes an audit log entry.

## Quick reminders

| Area | Do | Don't |
|---|---|---|
| Catalog | Variant + versioned recipe | Treat product as inventoriable SKU |
| Units | Stay in base unit | Silent unit conversion without density |
| Numbers | `Decimal` / `NUMERIC` | `float` / `number` for money or qty |
| Stock | Append movements + update balance atomically | Mutate history or update balance alone |
| Confirm | Idempotent txn + ordered row locks | Deduct on draft / fire / pay as side effects |
| Modifiers | Fold into effective recipe | Deduct base recipe then patch ad hoc |
| Costing | Snapshot at sale | Recompute past COGS |
| Purchasing | Receipt confirms stock + WAC | Receive stock on PO create/approve |
| Batches | FEFO | Arbitrary / LIFO without reason |
| Cancel | Reversal or manager waste/return + audit | Silent delete of movements |
