"""Auth & identity schemas."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr

from app.schemas.common import ORMBase


class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshIn(BaseModel):
    refresh_token: str


class UserOut(ORMBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    email: str
    display_name: str
    status: str
    locale: str
    title: str | None = None
    primary_unit_id: uuid.UUID | None = None
    is_external: bool = False


class MeOut(BaseModel):
    user: UserOut
    permissions: list[str]
    system_roles: list[str]
    is_admin: bool


class UserCreate(BaseModel):
    email: EmailStr
    display_name: str
    password: str | None = None
    title: str | None = None
    primary_unit_id: uuid.UUID | None = None
    employee_code: str | None = None
    roles: list[str] = []  # built-in role codes to assign


class UserUpdate(BaseModel):
    display_name: str | None = None
    status: str | None = None
    title: str | None = None
    primary_unit_id: uuid.UUID | None = None
    locale: str | None = None


class RoleAssignIn(BaseModel):
    user_id: uuid.UUID
    role_code: str
    scope_type: str | None = None
    scope_id: uuid.UUID | None = None
    reason: str | None = None
