from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import UnauthorizedError
from app.core.logging import request_id_ctx
from app.core.security import create_token, decode_token, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import RoleOut, TokenResponse, UserMeResponse
from app.services.audit_service import AuditService


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._audit = AuditService(session)

    async def login(
        self,
        email: str,
        password: str,
        *,
        ip_address: str | None = None,
    ) -> TokenResponse:
        user = await self._users.get_by_email(email)
        if user is None or not user.is_active:
            raise UnauthorizedError("Invalid email or password")
        if not verify_password(password, user.password_hash):
            raise UnauthorizedError("Invalid email or password")

        tokens = TokenResponse(
            access_token=create_token(user.id, "access"),
            refresh_token=create_token(user.id, "refresh"),
        )
        await self._audit.write(
            action="auth.login",
            entity_type="user",
            entity_id=str(user.id),
            user_id=user.id,
            after={"email": user.email},
            ip_address=ip_address,
            request_id=request_id_ctx.get(),
        )
        await self._session.commit()
        return tokens

    async def refresh(self, refresh_token: str) -> TokenResponse:
        payload = decode_token(refresh_token, "refresh")
        user_id = UUID(payload["sub"])
        user = await self._users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("Invalid refresh token")
        return TokenResponse(
            access_token=create_token(user.id, "access"),
            refresh_token=create_token(user.id, "refresh"),
        )

    async def get_me(self, user_id: UUID) -> UserMeResponse:
        user = await self._users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("User not found")
        return self.to_me_response(user)

    @staticmethod
    def to_me_response(user: User) -> UserMeResponse:
        return UserMeResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            roles=[
                RoleOut(code=role.code, name_en=role.name_en, name_ar=role.name_ar)
                for role in user.roles
            ],
            permissions=sorted(user.permission_codes()),
            branch_id=user.branch_id,
        )
