from __future__ import annotations

import hashlib
import secrets
import time
from collections import deque
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import AppError, ForbiddenError, NotFoundError
from app.core.security import verify_password
from app.models.catalog import Ingredient, ProductVariant
from app.models.inventory import InventoryBatch
from app.models.sales import Sale, SaleItem
from app.models.scanner import ScannerSession
from app.models.user import User
from app.schemas.scanner import ScanEventResponse, ScanResolveResponse
from app.services.sales_service import SalesService
from app.services.scanner_realtime import publish_station_event

PAIRING_TTL = timedelta(minutes=2)
MAX_SESSION_TTL = timedelta(hours=12)
SCAN_RATE_LIMIT = 60
SCAN_RATE_WINDOW_SECONDS = 60

_scan_windows: dict[str, deque[float]] = {}
_seen_events: set[tuple[str, str]] = set()
_session_draft_sales: dict[str, UUID] = {}


class ScannerService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_session(
        self,
        *,
        station_id: UUID,
        user_id: UUID,
        mode: str,
        expires_hours: int,
    ) -> tuple[ScannerSession, str]:
        now = datetime.now(UTC)
        pairing_token = self._new_token("pair")
        expires_delta = min(timedelta(hours=expires_hours), MAX_SESSION_TTL)
        scanner_session = ScannerSession(
            station_id=station_id,
            user_id=user_id,
            mode=mode,
            status="PAIRING",
            pairing_token_hash=self._hash_token(pairing_token),
            pairing_expires_at=now + PAIRING_TTL,
            expires_at=now + expires_delta,
            created_at=now,
        )
        self._session.add(scanner_session)
        await self._session.flush()
        return scanner_session, pairing_token

    async def pair(self, pairing_token: str) -> tuple[ScannerSession, str]:
        token_hash = self._hash_token(pairing_token)
        now = datetime.now(UTC)
        result = await self._session.execute(
            select(ScannerSession).where(ScannerSession.pairing_token_hash == token_hash)
        )
        scanner_session = result.scalar_one_or_none()
        if scanner_session is None:
            raise ForbiddenError("Invalid pairing token", code="INVALID_PAIRING_TOKEN")
        if scanner_session.status != "PAIRING" or scanner_session.pairing_expires_at < now:
            raise ForbiddenError("Pairing token expired", code="PAIRING_TOKEN_EXPIRED")
        if scanner_session.expires_at < now:
            scanner_session.status = "EXPIRED"
            raise ForbiddenError("Scanner session expired", code="SCANNER_SESSION_EXPIRED")

        device_token = self._new_token("scn")
        scanner_session.device_token_hash = self._hash_token(device_token)
        scanner_session.pairing_token_hash = None
        scanner_session.status = "PAIRED"
        await self._session.flush()
        return scanner_session, device_token

    async def get_session_by_device_token(self, device_token: str) -> ScannerSession:
        result = await self._session.execute(
            select(ScannerSession)
            .where(ScannerSession.device_token_hash == self._hash_token(device_token))
            .options(selectinload(ScannerSession.user))
        )
        scanner_session = result.scalar_one_or_none()
        if scanner_session is None:
            raise ForbiddenError("Invalid scanner device token", code="INVALID_SCANNER_TOKEN")

        now = datetime.now(UTC)
        if scanner_session.status != "PAIRED" or scanner_session.expires_at < now:
            scanner_session.status = "EXPIRED"
            raise ForbiddenError("Scanner session expired", code="SCANNER_SESSION_EXPIRED")
        return scanner_session

    async def resolve_code(self, code: str) -> ScanResolveResponse:
        stripped = code.strip()
        if not stripped:
            raise NotFoundError("Code not found", code="CODE_NOT_FOUND")

        try:
            entity_id = UUID(stripped)
        except ValueError:
            entity_id = None

        if entity_id is not None:
            batch = await self._session.get(InventoryBatch, entity_id)
            if batch is not None:
                ingredient = await self._session.get(Ingredient, batch.ingredient_id)
                if ingredient is None:
                    raise NotFoundError("Code not found", code="CODE_NOT_FOUND")
                return ScanResolveResponse(
                    type="batch",
                    id=batch.id,
                    code=stripped,
                    name_en=ingredient.name_en,
                    name_ar=ingredient.name_ar,
                    ingredient_id=ingredient.id,
                    remaining_qty=Decimal(batch.remaining_qty),
                )

            variant = await self._session.get(ProductVariant, entity_id)
            if variant is not None:
                return self._variant_response(stripped, variant)

            ingredient = await self._session.get(Ingredient, entity_id)
            if ingredient is not None:
                return self._ingredient_response(stripped, ingredient)

        variant_result = await self._session.execute(
            select(ProductVariant).where(ProductVariant.barcode == stripped)
        )
        variants = list(variant_result.scalars().all())
        ingredient_result = await self._session.execute(
            select(Ingredient).where(Ingredient.barcode == stripped)
        )
        ingredients = list(ingredient_result.scalars().all())
        matches = len(variants) + len(ingredients)
        if matches > 1:
            raise AppError(
                "DUPLICATE_BARCODE",
                "Barcode resolves to more than one item",
                status_code=status.HTTP_409_CONFLICT,
            )
        if variants:
            return self._variant_response(stripped, variants[0])
        if ingredients:
            return self._ingredient_response(stripped, ingredients[0])
        raise NotFoundError("Code not found", code="CODE_NOT_FOUND")

    async def process_scan(
        self,
        *,
        device_token: str,
        event_id: str,
        code: str,
        qty: int,
        pin: str | None = None,
    ) -> ScanEventResponse:
        scanner_session = await self.get_session_by_device_token(device_token)
        self._check_rate_limit(device_token)

        dedupe_key = (str(scanner_session.id), event_id)
        if dedupe_key in _seen_events:
            return ScanEventResponse(
                event_id=event_id,
                duplicate=True,
                session_id=scanner_session.id,
                mode=scanner_session.mode,  # type: ignore[arg-type]
                message="Duplicate event ignored",
            )

        if scanner_session.mode == "WASTE":
            await self._verify_waste_pin(scanner_session.user, pin)

        resolved = await self.resolve_code(code)
        sale_id: UUID | None = None
        if scanner_session.mode == "CASHIER" and resolved.type == "variant":
            sale = await self._add_to_draft_sale(scanner_session, resolved.id, qty)
            sale_id = sale.id

        event = {
            "type": "scanner.scan",
            "event_id": event_id,
            "session_id": str(scanner_session.id),
            "station_id": str(scanner_session.station_id),
            "mode": scanner_session.mode,
            "qty": qty,
            "resolved": resolved.model_dump(mode="json"),
            "sale_id": str(sale_id) if sale_id else None,
        }
        await publish_station_event(str(scanner_session.station_id), event)
        _seen_events.add(dedupe_key)
        return ScanEventResponse(
            event_id=event_id,
            duplicate=False,
            session_id=scanner_session.id,
            mode=scanner_session.mode,  # type: ignore[arg-type]
            resolved=resolved,
            sale_id=sale_id,
            message="Scan accepted",
        )

    async def _add_to_draft_sale(
        self,
        scanner_session: ScannerSession,
        variant_id: UUID,
        qty: int,
    ) -> Sale:
        user = await self._session.get(User, scanner_session.user_id)
        if user is None or user.branch_id is None:
            raise AppError("SCANNER_USER_INVALID", "Scanner user is missing a branch")

        service = SalesService(self._session)
        sale = None
        draft_sale_id = _session_draft_sales.get(str(scanner_session.id))
        if draft_sale_id is not None:
            result = await self._session.execute(
                select(Sale)
                .where(Sale.id == draft_sale_id, Sale.status == "DRAFT")
                .options(selectinload(Sale.items).selectinload(SaleItem.modifiers))
            )
            sale = result.scalar_one_or_none()

        if sale is None:
            sale = await service.create_sale(
                branch_id=user.branch_id,
                user_id=user.id,
                order_type="dine_in",
                items=[{"variant_id": variant_id, "qty": qty}],
            )
            _session_draft_sales[str(scanner_session.id)] = sale.id
            return sale

        items = [
            {
                "variant_id": item.variant_id,
                "qty": item.qty + qty if item.variant_id == variant_id else item.qty,
                "modifier_ids": [modifier.modifier_id for modifier in item.modifiers],
                "notes": item.notes,
            }
            for item in sale.items
        ]
        if all(item["variant_id"] != variant_id for item in items):
            items.append({"variant_id": variant_id, "qty": qty})
        return await service.update_sale(sale.id, items=items)

    async def _verify_waste_pin(self, user: User, pin: str | None) -> None:
        if not pin:
            raise ForbiddenError("Waste scans require operator PIN", code="PIN_REQUIRED")
        pin_hash = user.pin_hash or user.password_hash
        if not verify_password(pin, pin_hash):
            raise ForbiddenError("Invalid operator PIN", code="INVALID_PIN")

    def _check_rate_limit(self, device_token: str) -> None:
        now = time.monotonic()
        token_hash = self._hash_token(device_token)
        window = _scan_windows.setdefault(token_hash, deque())
        while window and now - window[0] > SCAN_RATE_WINDOW_SECONDS:
            window.popleft()
        if len(window) >= SCAN_RATE_LIMIT:
            raise AppError(
                "SCAN_RATE_LIMITED",
                "Too many scans from this device",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        window.append(now)

    def _variant_response(self, code: str, variant: ProductVariant) -> ScanResolveResponse:
        return ScanResolveResponse(
            type="variant",
            id=variant.id,
            code=code,
            sku=variant.sku,
            name_en=variant.name_en,
            name_ar=variant.name_ar,
            price=Decimal(variant.price),
        )

    def _ingredient_response(self, code: str, ingredient: Ingredient) -> ScanResolveResponse:
        return ScanResolveResponse(
            type="ingredient",
            id=ingredient.id,
            code=code,
            sku=ingredient.sku,
            name_en=ingredient.name_en,
            name_ar=ingredient.name_ar,
        )

    def _new_token(self, prefix: str) -> str:
        return f"{prefix}_{secrets.token_urlsafe(32)}"

    def _hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
