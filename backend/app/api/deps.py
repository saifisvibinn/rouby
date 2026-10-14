from collections.abc import Awaitable, Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.models.user import User
from app.repositories.user_repository import UserRepository

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    db: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    if token.startswith("scn_"):
        raise ForbiddenError("Scanner device tokens cannot access user endpoints")
    payload = decode_token(token, "access")
    user = await UserRepository(db).get_by_id(UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_permissions(
    *required: str,
) -> Callable[[User], Awaitable[User]]:
    async def _checker(user: CurrentUser) -> User:
        have = user.permission_codes()
        missing = [code for code in required if code not in have]
        if missing:
            raise ForbiddenError(
                "Missing required permissions",
                code="FORBIDDEN",
            )
        return user

    return _checker
