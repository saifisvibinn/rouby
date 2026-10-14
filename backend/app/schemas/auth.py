from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: str = Field(min_length=1)
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class RoleOut(BaseModel):
    code: str
    name_en: str
    name_ar: str

    model_config = {"from_attributes": True}


class UserMeResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    roles: list[RoleOut]
    permissions: list[str]
    branch_id: UUID | None

    model_config = {"from_attributes": True}
