import pytest
from app.models.audit import AuditLog
from app.seed.permissions import OPERATOR_PERMISSIONS
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

PREFIX = "/api/v1/auth"
DEMO_EMAIL = "admin@rouby.app"
DEMO_PASSWORD = "admin"


@pytest.mark.asyncio
async def test_login_operator(client: AsyncClient) -> None:
    response = await client.post(
        f"{PREFIX}/login",
        json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

    me = await client.get(
        f"{PREFIX}/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == DEMO_EMAIL
    assert any(r["code"] == "OPERATOR" for r in body["roles"])
    assert set(body["permissions"]) == set(OPERATOR_PERMISSIONS)


@pytest.mark.asyncio
async def test_login_accepts_plain_username(client: AsyncClient) -> None:
    response = await client.post(
        f"{PREFIX}/login",
        json={"email": "admin", "password": "admin"},
    )
    assert response.status_code == 200, response.text



@pytest.mark.asyncio
async def test_invalid_password(client: AsyncClient) -> None:
    response = await client.post(
        f"{PREFIX}/login",
        json={"email": DEMO_EMAIL, "password": "wrong"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_refresh_returns_new_access(client: AsyncClient) -> None:
    login = await client.post(
        f"{PREFIX}/login",
        json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
    )
    refresh_token = login.json()["refresh_token"]
    refreshed = await client.post(
        f"{PREFIX}/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refreshed.status_code == 200
    assert "access_token" in refreshed.json()


@pytest.mark.asyncio
async def test_me_without_token(client: AsyncClient) -> None:
    response = await client.get(f"{PREFIX}/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_operator_has_full_access(client: AsyncClient) -> None:
    login = await client.post(
        f"{PREFIX}/login",
        json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
    )
    token = login.json()["access_token"]
    me = await client.get(f"{PREFIX}/me", headers={"Authorization": f"Bearer {token}"})
    perms = set(me.json()["permissions"])
    assert "products.edit" in perms
    assert "recipes.edit" in perms
    assert "reports.view_profit" in perms
    assert "inventory.adjust" in perms
    assert "sales.cancel" in perms


@pytest.mark.asyncio
async def test_login_writes_audit_log(client: AsyncClient, engine) -> None:
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        before = await session.execute(select(AuditLog).where(AuditLog.action == "auth.login"))
        count_before = len(before.scalars().all())

    response = await client.post(
        f"{PREFIX}/login",
        json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200

    async with session_factory() as session:
        result = await session.execute(
            select(AuditLog)
            .where(AuditLog.action == "auth.login")
            .order_by(AuditLog.created_at.desc())
        )
        rows = list(result.scalars().all())
        assert len(rows) >= count_before + 1
        latest = rows[0]
        assert latest.entity_type == "user"
        assert latest.after is not None
        assert latest.after.get("email") == DEMO_EMAIL
