from typing import Annotated

from fastapi import APIRouter, Depends, Header, status

from app.api.deps import CurrentUser, DbSession, require_permissions
from app.core.errors import ForbiddenError
from app.schemas.scanner import (
    ScanEventRequest,
    ScanEventResponse,
    ScannerPairRequest,
    ScannerPairResponse,
    ScannerSessionCreate,
    ScannerSessionCreateResponse,
    ScanResolveResponse,
)
from app.services.scanner_service import ScannerService

router = APIRouter(tags=["scanner"])


def _device_token_from_headers(
    x_scanner_device_token: str | None,
    authorization: str | None,
) -> str:
    if x_scanner_device_token:
        return x_scanner_device_token
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1].strip()
    raise ForbiddenError("Missing scanner device token", code="SCANNER_TOKEN_REQUIRED")


@router.post(
    "/scanner/sessions",
    response_model=ScannerSessionCreateResponse,
    dependencies=[Depends(require_permissions("sales.create"))],
    status_code=status.HTTP_201_CREATED,
)
async def create_scanner_session(
    body: ScannerSessionCreate,
    user: CurrentUser,
    db: DbSession,
) -> ScannerSessionCreateResponse:
    scanner_session, pairing_token = await ScannerService(db).create_session(
        station_id=body.station_id,
        user_id=user.id,
        mode=body.mode,
        expires_hours=body.expires_hours,
    )
    await db.commit()
    return ScannerSessionCreateResponse(
        session_id=scanner_session.id,
        pairing_token=pairing_token,
        pairing_expires_at=scanner_session.pairing_expires_at,
        qr_path=f"/scanner?pair={pairing_token}",
    )


@router.post("/scanner/pair", response_model=ScannerPairResponse)
async def pair_scanner(
    body: ScannerPairRequest,
    db: DbSession,
) -> ScannerPairResponse:
    scanner_session, device_token = await ScannerService(db).pair(body.pairing_token)
    await db.commit()
    return ScannerPairResponse(
        session_id=scanner_session.id,
        device_token=device_token,
        mode=scanner_session.mode,  # type: ignore[arg-type]
        expires_at=scanner_session.expires_at,
    )


@router.get("/scan/resolve/{code}", response_model=ScanResolveResponse)
async def resolve_scan_code(
    code: str,
    db: DbSession,
    x_scanner_device_token: Annotated[str | None, Header()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> ScanResolveResponse:
    service = ScannerService(db)
    device_token = _device_token_from_headers(x_scanner_device_token, authorization)
    await service.get_session_by_device_token(device_token)
    return await service.resolve_code(code)


@router.post("/scan/events", response_model=ScanEventResponse)
async def submit_scan_event(
    body: ScanEventRequest,
    db: DbSession,
    x_scanner_device_token: Annotated[str | None, Header()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> ScanEventResponse:
    device_token = _device_token_from_headers(x_scanner_device_token, authorization)
    result = await ScannerService(db).process_scan(
        device_token=device_token,
        event_id=body.event_id,
        code=body.code,
        qty=body.qty,
        pin=body.pin,
    )
    await db.commit()
    return result
