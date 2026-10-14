"""Permission catalog for single-operator home deployment."""

ALL_PERMISSIONS: list[tuple[str, str]] = [
    ("products.edit", "Create and edit products and prices"),
    ("products.view", "View products"),
    ("recipes.edit", "Edit recipes"),
    ("recipes.view", "View recipes"),
    ("sales.create", "Create and confirm sales"),
    ("sales.view", "View sales"),
    ("sales.cancel", "Cancel sales"),
    ("inventory.adjust", "Manual stock adjustments"),
    ("inventory.receive", "Receive goods"),
    ("inventory.count", "Stock counts"),
    ("inventory.waste", "Record waste"),
    ("inventory.view", "View inventory"),
    ("reports.view", "View non-profit reports"),
    ("reports.view_profit", "View profit / COGS reports"),
    ("users.manage", "Manage users and roles"),
    ("settings.edit", "Edit system settings"),
]

# # DECISION: single-operator home restaurant — one role with full access; no staff roles
OPERATOR_PERMISSIONS = [code for code, _ in ALL_PERMISSIONS]

ROLE_PERMISSION_MAP: dict[str, list[str]] = {
    "OPERATOR": OPERATOR_PERMISSIONS,
}

# # DECISION: use @rouby.app (not .local) — EmailStr rejects reserved TLDs
# Login accepts plain "admin" (normalized to admin@rouby.app) or the full email.
DEMO_USERS: list[dict[str, str]] = [
    {
        "email": "admin@rouby.app",
        "full_name": "Admin",
        "password": "admin",
        "role": "OPERATOR",
    },
]
