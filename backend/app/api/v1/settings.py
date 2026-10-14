from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.settings import Setting
from app.schemas.settings import SettingOut

router = APIRouter(tags=["settings"])


@router.get("/settings", response_model=list[SettingOut])
async def list_settings(db: DbSession, _user: CurrentUser) -> list[SettingOut]:
    result = await db.execute(select(Setting).order_by(Setting.key))
    return list(result.scalars().all())
