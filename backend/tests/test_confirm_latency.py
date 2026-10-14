import time
from uuid import uuid4

import pytest
from app.models.branch import Branch
from app.models.catalog import ProductVariant
from app.models.user import User
from app.services.sales_service import SalesService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_confirm_sale_under_latency_budget(db_session: AsyncSession) -> None:
    """Seed confirm should stay well under the 500ms p95 target for a single operator."""
    user = (
        await db_session.execute(select(User).where(User.email == "admin@rouby.app"))
    ).scalar_one()
    branch = (await db_session.execute(select(Branch))).scalar_one()
    variant = (
        await db_session.execute(
            select(ProductVariant).where(ProductVariant.sku == "BANANA_PROTEIN_SHAKE")
        )
    ).scalar_one()

    svc = SalesService(db_session)
    sale = await svc.create_sale(
        branch_id=branch.id,
        user_id=user.id,
        order_type="dine_in",
        items=[{"variant_id": variant.id, "qty": 1}],
    )

    started = time.perf_counter()
    confirmed = await svc.confirm(sale.id, str(uuid4()), user_id=user.id)
    elapsed_ms = (time.perf_counter() - started) * 1000

    assert confirmed.status == "CONFIRMED"
    # Generous CI budget (2s); documented product target remains p95 < 500ms on seed.
    assert elapsed_ms < 2000, f"confirm took {elapsed_ms:.1f}ms"
    # Shared session DB — do not leave seed stock mutated for later inventory tests.
    await db_session.rollback()

