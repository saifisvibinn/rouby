from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from app.models.catalog import Ingredient, ProductVariant
from app.models.sales import Sale
from app.models.scanner import ScannerSession
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

DEMO_EMAIL = "admin@rouby.app"
DEMO_PASSWORD = "admin"


async def _auth_headers(client: AsyncClient) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def _create_pairing(
    client: AsyncClient,
    *,
    mode: str = "CASHIER",
    station_id: UUID | None = None,
) -> dict:
    response = await client.post(
        "/api/v1/scanner/sessions",
        headers=await _auth_headers(client),
        json={
            "station_id": str(station_id or uuid4()),
            "mode": mode,
            "expires_hours": 12,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _pair(client: AsyncClient, pairing_token: str) -> dict:
    response = await client.post(
        "/api/v1/scanner/pair",
        json={"pairing_token": pairing_token},
    )
    assert response.status_code == 200, response.text
    return response.json()


async def _variant(session: AsyncSession, sku: str = "BANANA_PROTEIN_SHAKE") -> ProductVariant:
    result = await session.execute(select(ProductVariant).where(ProductVariant.sku == sku))
    return result.scalar_one()


async def _ingredient(session: AsyncSession, sku: str = "MILK") -> Ingredient:
    result = await session.execute(select(Ingredient).where(Ingredient.sku == sku))
    return result.scalar_one()


@pytest.mark.asyncio
async def test_pairing_token_single_use_and_expiry(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    pairing = await _create_pairing(client)
    paired = await _pair(client, pairing["pairing_token"])
    assert paired["session_id"] == pairing["session_id"]

    reused = await client.post(
        "/api/v1/scanner/pair",
        json={"pairing_token": pairing["pairing_token"]},
    )
    assert reused.status_code == 403
    assert reused.json()["error"]["code"] == "INVALID_PAIRING_TOKEN"

    expired_pairing = await _create_pairing(client)
    scanner_session = await db_session.get(
        ScannerSession,
        UUID(expired_pairing["session_id"]),
    )
    assert scanner_session is not None
    scanner_session.pairing_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    await db_session.commit()

    expired = await client.post(
        "/api/v1/scanner/pair",
        json={"pairing_token": expired_pairing["pairing_token"]},
    )
    assert expired.status_code == 403
    assert expired.json()["error"]["code"] == "PAIRING_TOKEN_EXPIRED"


@pytest.mark.asyncio
async def test_device_token_cannot_call_auth_me(client: AsyncClient) -> None:
    pairing = await _create_pairing(client)
    paired = await _pair(client, pairing["pairing_token"])

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {paired['device_token']}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cashier_scan_adds_to_draft_and_dedupes_event_id(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    variant = await _variant(db_session)
    barcode = f"scan-{uuid4()}"
    variant.barcode = barcode
    await db_session.commit()

    pairing = await _create_pairing(client)
    paired = await _pair(client, pairing["pairing_token"])
    headers = {"X-Scanner-Device-Token": paired["device_token"]}
    payload = {"event_id": "scan-event-1", "code": barcode, "qty": 2}

    first = await client.post("/api/v1/scan/events", headers=headers, json=payload)
    assert first.status_code == 200, first.text
    assert first.json()["sale_id"] is not None

    duplicate = await client.post("/api/v1/scan/events", headers=headers, json=payload)
    assert duplicate.status_code == 200, duplicate.text
    assert duplicate.json()["duplicate"] is True

    sale_id = UUID(first.json()["sale_id"])
    result = await db_session.execute(
        select(Sale).where(Sale.id == sale_id).options(selectinload(Sale.items))
    )
    sale = result.scalar_one()
    assert sale.status == "DRAFT"
    assert len(sale.items) == 1
    assert sale.items[0].variant_id == variant.id
    assert sale.items[0].qty == 2


@pytest.mark.asyncio
async def test_code_not_found(client: AsyncClient) -> None:
    pairing = await _create_pairing(client)
    paired = await _pair(client, pairing["pairing_token"])

    response = await client.get(
        f"/api/v1/scan/resolve/not-found-{uuid4()}",
        headers={"X-Scanner-Device-Token": paired["device_token"]},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CODE_NOT_FOUND"


@pytest.mark.asyncio
async def test_duplicate_barcode_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    barcode = f"duplicate-{uuid4()}"
    variant = await _variant(db_session, "CHICKEN_WRAP")
    ingredient = await _ingredient(db_session, "WHEY")
    variant.barcode = barcode
    ingredient.barcode = barcode
    await db_session.commit()

    pairing = await _create_pairing(client)
    paired = await _pair(client, pairing["pairing_token"])
    response = await client.get(
        f"/api/v1/scan/resolve/{barcode}",
        headers={"X-Scanner-Device-Token": paired["device_token"]},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DUPLICATE_BARCODE"
