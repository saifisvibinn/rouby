from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import JWTError, jwt

from app.core.errors import UnauthorizedError
from app.core.settings import get_settings

password_hasher = PasswordHasher()
TokenType = Literal["access", "refresh"]


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def create_token(
    subject: UUID,
    token_type: TokenType,
    *,
    expires_delta: timedelta | None = None,
) -> str:
    settings = get_settings()
    if expires_delta is None:
        if token_type == "access":
            expires_delta = timedelta(minutes=settings.access_token_expire_minutes)
        else:
            expires_delta = timedelta(days=settings.refresh_token_expire_days)

    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected_type: TokenType) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise UnauthorizedError("Invalid or expired token", code="INVALID_TOKEN") from exc

    if payload.get("type") != expected_type:
        raise UnauthorizedError("Invalid token type", code="INVALID_TOKEN_TYPE")
    if not payload.get("sub"):
        raise UnauthorizedError("Invalid token subject", code="INVALID_TOKEN")
    return payload
