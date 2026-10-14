from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, DbSession, require_permissions
from app.schemas.inventory import (
    GoodsReceiptCreate,
    GoodsReceiptOut,
    InventoryBalanceOut,
    LocationOut,
    PurchaseOrderCreate,
    StockCountCreate,
    StockCountOut,
    StockMovementOut,
    WasteCreate,
    WasteOut,
)
from app.services.inventory_service import InventoryService

router = APIRouter(tags=["inventory"])


@router.get("/locations", response_model=list[LocationOut])
async def list_locations(user: CurrentUser, db: DbSession) -> list[LocationOut]:
    return await InventoryService(db).list_locations(user.branch_id)


@router.post(
    "/purchase-orders",
    dependencies=[Depends(require_permissions("inventory.receive"))],
)
async def create_purchase_order(
    body: PurchaseOrderCreate,
    user: CurrentUser,
    db: DbSession,
) -> dict[str, UUID]:
    order = await InventoryService(db).create_purchase_order(
        branch_id=body.branch_id,
        supplier_id=body.supplier_id,
        items=[item.model_dump() for item in body.items],
        user_id=user.id,
        notes=body.notes,
    )
    await db.commit()
    return {"id": order.id}


@router.post(
    "/goods-receipts",
    response_model=GoodsReceiptOut,
    dependencies=[Depends(require_permissions("inventory.receive"))],
)
async def create_goods_receipt(
    body: GoodsReceiptCreate,
    user: CurrentUser,
    db: DbSession,
) -> GoodsReceiptOut:
    service = InventoryService(db)
    receipt = await service.create_goods_receipt(
        location_id=body.location_id,
        supplier_id=body.supplier_id,
        purchase_order_id=body.purchase_order_id,
        items=[item.model_dump() for item in body.items],
        user_id=user.id,
        notes=body.notes,
    )
    if body.confirm:
        receipt = await service.confirm_goods_receipt(receipt.id, user_id=user.id)
    await db.commit()
    return receipt


@router.post(
    "/goods-receipts/{receipt_id}/confirm",
    response_model=GoodsReceiptOut,
    dependencies=[Depends(require_permissions("inventory.receive"))],
)
async def confirm_goods_receipt(
    receipt_id: UUID,
    user: CurrentUser,
    db: DbSession,
) -> GoodsReceiptOut:
    receipt = await InventoryService(db).confirm_goods_receipt(receipt_id, user_id=user.id)
    await db.commit()
    return receipt


@router.post(
    "/waste",
    response_model=WasteOut,
    dependencies=[Depends(require_permissions("inventory.waste"))],
)
async def create_waste(
    body: WasteCreate,
    user: CurrentUser,
    db: DbSession,
) -> WasteOut:
    record = await InventoryService(db).apply_waste(
        ingredient_id=body.ingredient_id,
        location_id=body.location_id,
        quantity_base=body.quantity_base,
        reason=body.reason,
        user_id=user.id,
    )
    await db.commit()
    return record


@router.post(
    "/stock-counts",
    response_model=StockCountOut,
    dependencies=[Depends(require_permissions("inventory.count"))],
)
async def create_stock_count(
    body: StockCountCreate,
    user: CurrentUser,
    db: DbSession,
) -> StockCountOut:
    service = InventoryService(db)
    count = await service.create_stock_count(
        location_id=body.location_id,
        items=[item.model_dump() for item in body.items],
        user_id=user.id,
        notes=body.notes,
    )
    if body.post:
        count = await service.post_stock_count_variance(count.id, user_id=user.id)
    await db.commit()
    return count


@router.post(
    "/stock-counts/{stock_count_id}/post",
    response_model=StockCountOut,
    dependencies=[Depends(require_permissions("inventory.count"))],
)
async def post_stock_count(
    stock_count_id: UUID,
    user: CurrentUser,
    db: DbSession,
) -> StockCountOut:
    count = await InventoryService(db).post_stock_count_variance(stock_count_id, user_id=user.id)
    await db.commit()
    return count


@router.get(
    "/inventory/balances",
    response_model=list[InventoryBalanceOut],
    dependencies=[Depends(require_permissions("inventory.view"))],
)
async def list_inventory_balances(
    _user: CurrentUser,
    db: DbSession,
) -> list[InventoryBalanceOut]:
    return await InventoryService(db).list_balances()


@router.get(
    "/stock-movements",
    response_model=list[StockMovementOut],
    dependencies=[Depends(require_permissions("inventory.view"))],
)
async def list_stock_movements(
    _user: CurrentUser,
    db: DbSession,
) -> list[StockMovementOut]:
    return await InventoryService(db).list_movements()
