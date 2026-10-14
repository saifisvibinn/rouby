from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Response

from app.api.deps import CurrentUser, DbSession, require_permissions
from app.services.report_service import ReportService

router = APIRouter(tags=["reports"])


def _csv_response(content: str, filename: str) -> Response:
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/reports/sales",
    response_model=None,
    dependencies=[Depends(require_permissions("reports.view"))],
)
async def get_sales_report(
    _user: CurrentUser,
    db: DbSession,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: datetime | None = None,
    format: Literal["json", "csv"] = "json",
) -> dict[str, Any] | Response:
    service = ReportService(db)
    report = await service.sales_report(from_at=from_, to_at=to)
    if format == "csv":
        return _csv_response(service.sales_csv(report), "sales-report.csv")
    return report


@router.get(
    "/reports/inventory",
    dependencies=[Depends(require_permissions("reports.view"))],
)
async def get_inventory_report(
    _user: CurrentUser,
    db: DbSession,
) -> dict[str, Any]:
    return await ReportService(db).inventory_report()


@router.get(
    "/reports/profit",
    response_model=None,
    dependencies=[Depends(require_permissions("reports.view_profit"))],
)
async def get_profit_report(
    _user: CurrentUser,
    db: DbSession,
    from_: Annotated[datetime | None, Query(alias="from")] = None,
    to: datetime | None = None,
    format: Literal["json", "csv"] = "json",
) -> dict[str, Any] | Response:
    service = ReportService(db)
    report = await service.profit_report(from_at=from_, to_at=to)
    if format == "csv":
        return _csv_response(service.profit_csv(report), "profit-report.csv")
    return report


@router.get(
    "/reports/usage-variance",
    dependencies=[Depends(require_permissions("reports.view_profit"))],
)
async def get_usage_variance_report(
    _user: CurrentUser,
    db: DbSession,
) -> dict[str, Any]:
    return await ReportService(db).usage_variance_report()


@router.get(
    "/reports/reorder-suggestions",
    dependencies=[Depends(require_permissions("reports.view"))],
)
async def get_reorder_suggestions(
    _user: CurrentUser,
    db: DbSession,
    days: int = Query(30, ge=1),
    lead_time: int = Query(3, ge=1),
) -> dict[str, Any]:
    return await ReportService(db).reorder_suggestions(days=days, lead_time_days=lead_time)
