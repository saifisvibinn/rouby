from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.scanner import ScannerSession
from app.schemas.scanner import ScanEventRequest
from app.services.scanner_realtime import station_subscription
from app.services.scanner_service import ScannerService

router = APIRouter()


async def _ws_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db():
        yield session


WsDbSession = Annotated[AsyncSession, Depends(_ws_db)]


@router.websocket("/ws/station")
async def station_websocket(
    websocket: WebSocket,
    session_id: str,
    db: WsDbSession,
) -> None:
    scanner_session = await db.get(ScannerSession, session_id)
    if scanner_session is None:
        await websocket.close(code=4404)
        return

    await websocket.accept()
    async with station_subscription(str(scanner_session.station_id)) as queue:
        try:
            while True:
                await websocket.send_text(await queue.get())
        except WebSocketDisconnect:
            return


@router.websocket("/ws/scanner")
async def scanner_websocket(
    websocket: WebSocket,
    device_token: str,
    db: WsDbSession,
) -> None:
    await websocket.accept()
    service = ScannerService(db)
    try:
        scanner_session = await service.get_session_by_device_token(device_token)
    except Exception:
        await websocket.close(code=4403)
        return

    await websocket.send_json(
        {
            "type": "scanner.ready",
            "session_id": str(scanner_session.id),
            "mode": scanner_session.mode,
        }
    )
    try:
        while True:
            payload = json.loads(await websocket.receive_text())
            body = ScanEventRequest.model_validate(payload)
            result = await service.process_scan(
                device_token=device_token,
                event_id=body.event_id,
                code=body.code,
                qty=body.qty,
                pin=body.pin,
            )
            await db.commit()
            await websocket.send_json(result.model_dump(mode="json"))
    except WebSocketDisconnect:
        return
