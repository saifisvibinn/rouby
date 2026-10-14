from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import hash_password
from app.models.branch import Branch, Location
from app.models.settings import Setting
from app.models.user import Permission, Role, User
from app.seed.catalog import seed_catalog
from app.seed.inventory import seed_inventory
from app.seed.permissions import (
    ALL_PERMISSIONS,
    DEMO_USERS,
    ROLE_PERMISSION_MAP,
)


async def seed_all(session: AsyncSession) -> None:
    branch = await _ensure_branch(session)
    await _ensure_locations(session, branch)
    perms = await _ensure_permissions(session)
    roles = await _ensure_roles(session, perms)
    await _ensure_users(session, roles, branch)
    await seed_catalog(session)
    await seed_inventory(session)
    await _ensure_settings(session)
    await session.commit()


async def _ensure_branch(session: AsyncSession) -> Branch:
    result = await session.execute(select(Branch).where(Branch.code == "MAIN"))
    branch = result.scalar_one_or_none()
    if branch:
        return branch
    branch = Branch(
        code="MAIN",
        name_en="Main Branch",
        name_ar="الفرع الرئيسي",
    )
    session.add(branch)
    await session.flush()
    return branch


async def _ensure_locations(session: AsyncSession, branch: Branch) -> None:
    defaults = [
        ("FRIDGE", "Fridge", "ثلاجة"),
        ("DRY", "Dry Storage", "مخزن جاف"),
        ("PREP", "Prep Area", "منطقة التحضير"),
    ]
    for code, name_en, name_ar in defaults:
        result = await session.execute(
            select(Location).where(Location.branch_id == branch.id, Location.code == code)
        )
        if result.scalar_one_or_none():
            continue
        session.add(
            Location(
                branch_id=branch.id,
                code=code,
                name_en=name_en,
                name_ar=name_ar,
            )
        )


async def _ensure_permissions(session: AsyncSession) -> dict[str, Permission]:
    by_code: dict[str, Permission] = {}
    for code, description in ALL_PERMISSIONS:
        result = await session.execute(select(Permission).where(Permission.code == code))
        perm = result.scalar_one_or_none()
        if perm is None:
            perm = Permission(code=code, description=description)
            session.add(perm)
            await session.flush()
        by_code[code] = perm
    return by_code


async def _ensure_roles(
    session: AsyncSession,
    perms: dict[str, Permission],
) -> dict[str, Role]:
    role_meta = {
        "OPERATOR": ("Operator", "المشغّل"),
    }
    roles: dict[str, Role] = {}
    for code, (name_en, name_ar) in role_meta.items():
        result = await session.execute(
            select(Role)
            .where(Role.code == code)
            .options(selectinload(Role.permissions))
        )
        role = result.scalar_one_or_none()
        if role is None:
            role = Role(code=code, name_en=name_en, name_ar=name_ar)
            role.permissions = [perms[p] for p in ROLE_PERMISSION_MAP[code] if p in perms]
            session.add(role)
            await session.flush()
        else:
            role.permissions = [perms[p] for p in ROLE_PERMISSION_MAP[code] if p in perms]
        roles[code] = role
    await session.flush()
    return roles


async def _ensure_users(
    session: AsyncSession,
    roles: dict[str, Role],
    branch: Branch,
) -> None:
    # Migrate previous demo login if present
    legacy = await session.execute(
        select(User)
        .where(User.email == "operator@rouby.app")
        .options(selectinload(User.roles))
    )
    legacy_user = legacy.scalar_one_or_none()

    for demo in DEMO_USERS:
        email = demo["email"].lower()
        result = await session.execute(
            select(User).where(User.email == email).options(selectinload(User.roles))
        )
        user = result.scalar_one_or_none()
        if user is None and legacy_user is not None:
            user = legacy_user
            user.email = email
        if user is None:
            user = User(
                email=email,
                full_name=demo["full_name"],
                password_hash=hash_password(demo["password"]),
                branch_id=branch.id,
            )
            user.roles = [roles[demo["role"]]]
            session.add(user)
            await session.flush()
        else:
            user.full_name = demo["full_name"]
            user.password_hash = hash_password(demo["password"])
            user.roles = [roles[demo["role"]]]
            user.branch_id = branch.id
    await session.flush()


async def _ensure_settings(session: AsyncSession) -> None:
    defaults = [
        ("negative_stock_policy", "WARN", "BLOCK or WARN when stock is insufficient"),
        ("tax_rate", "0", "Tax rate percent; 0 until configured"),
        ("default_language", "en", "Default UI language"),
        ("discount_approval_threshold", "10", "Percent discount requiring manager approval"),
        ("currency", "EGP", "Store currency"),
    ]
    for key, value, description in defaults:
        result = await session.execute(select(Setting).where(Setting.key == key))
        if result.scalar_one_or_none():
            continue
        session.add(Setting(key=key, value=value, description=description))
