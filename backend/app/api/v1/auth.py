from fastapi import APIRouter, Request

from app.api.deps import CurrentUser, DbSession
from app.core.rate_limit import login_rate_limiter
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse, UserMeResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _normalize_login_email(raw: str) -> str:
    value = raw.strip().lower()
    if "@" not in value:
        return f"{value}@rouby.app"
    return value


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, db: DbSession) -> TokenResponse:
    ip = request.client.host if request.client else "unknown"
    email = _normalize_login_email(body.email)
    login_rate_limiter.check(f"login:{ip}:{email}")
    return await AuthService(db).login(email, body.password, ip_address=ip)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: DbSession) -> TokenResponse:
    return await AuthService(db).refresh(body.refresh_token)


@router.get("/me", response_model=UserMeResponse)
async def me(user: CurrentUser) -> UserMeResponse:
    return AuthService.to_me_response(user)
