from uuid import UUID

from fastapi import APIRouter, Depends, Header

from app.api.deps import CurrentUser, DbSession, require_permissions
from app.core.errors import AppError
from app.schemas.sales import (
    CancelRequest,
    PaymentIn,
    PaymentOut,
    SaleCreate,
    SaleOut,
    SaleUpdate,
    StatusUpdate,
)
from app.services.sales_service import SalesService

router = APIRouter(tags=["sales"])


@router.post(
    "/sales",
    response_model=SaleOut,
    dependencies=[Depends(require_permissions("sales.create"))],
)
async def create_sale(
    body: SaleCreate,
    user: CurrentUser,
    db: DbSession,
) -> SaleOut:
    sale = await SalesService(db).create_sale(
        branch_id=user.branch_id,
        user_id=user.id,
        order_type=body.order_type,
        items=[item.model_dump() for item in body.items],
        discount=body.discount,
    )
    await db.commit()
    return sale


@router.patch(
    "/sales/{sale_id}",
    response_model=SaleOut,
    dependencies=[Depends(require_permissions("sales.create"))],
)
async def update_sale(
    sale_id: UUID,
    body: SaleUpdate,
    _user: CurrentUser,
    db: DbSession,
) -> SaleOut:
    sale = await SalesService(db).update_sale(
        sale_id,
        items=[item.model_dump() for item in body.items] if body.items else None,
        discount=body.discount,
        order_type=body.order_type,
    )
    await db.commit()
    return sale


@router.post(
    "/sales/{sale_id}/confirm",
    response_model=SaleOut,
    dependencies=[Depends(require_permissions("sales.create"))],
)
async def confirm_sale(
    sale_id: UUID,
    user: CurrentUser,
    db: DbSession,
    idempotency_key: str = Header(alias="Idempotency-Key"),
) -> SaleOut:
    sale = await SalesService(db).confirm(
        sale_id,
        idempotency_key,
        user_id=user.id,
    )
    await db.commit()
    return sale


@router.post(
    "/sales/{sale_id}/status",
    response_model=SaleOut,
    dependencies=[Depends(require_permissions("sales.create"))],
)
async def update_status(
    sale_id: UUID,
    body: StatusUpdate,
    _user: CurrentUser,
    db: DbSession,
) -> SaleOut:
    sale = await SalesService(db).set_status(sale_id, body.status)
    await db.commit()
    return sale


@router.post(
    "/sales/{sale_id}/cancel",
    response_model=SaleOut,
    dependencies=[Depends(require_permissions("sales.cancel"))],
)
async def cancel_sale(
    sale_id: UUID,
    body: CancelRequest,
    user: CurrentUser,
    db: DbSession,
) -> SaleOut:
    sale = await SalesService(db).cancel(
        sale_id,
        user_id=user.id,
        line_dispositions=[d.model_dump() for d in body.line_dispositions],
    )
    await db.commit()
    return sale


@router.post(
    "/sales/{sale_id}/payments",
    response_model=PaymentOut,
    dependencies=[Depends(require_permissions("sales.create"))],
)
async def add_payment(
    sale_id: UUID,
    body: PaymentIn,
    _user: CurrentUser,
    db: DbSession,
) -> PaymentOut:
    payment = await SalesService(db).add_payment(
        sale_id,
        method=body.method,
        amount=body.amount,
    )
    await db.commit()
    return payment


@router.get(
    "/pos/menu",
    dependencies=[Depends(require_permissions("sales.view"))],
)
async def get_menu(
    user: CurrentUser,
    db: DbSession,
) -> list[dict]:
    return await SalesService(db).get_menu(user.branch_id)
