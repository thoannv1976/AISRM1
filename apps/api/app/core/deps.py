"""FastAPI dependencies: authentication, principal and permission guards."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.errors import AuthForbidden, AuthUnauthorized
from app.core.rbac import has_permission
from app.core.security import decode_token
from app.models.identity import Role, RoleAssignment, User

bearer = HTTPBearer(auto_error=False)


@dataclass
class Principal:
    user: User
    permissions: set[str] = field(default_factory=set)
    system_roles: set[str] = field(default_factory=set)
    unit_scopes: set[uuid.UUID] = field(default_factory=set)
    entity_scopes: set[tuple[str, uuid.UUID]] = field(default_factory=set)

    @property
    def id(self) -> uuid.UUID:
        return self.user.id

    @property
    def organization_id(self) -> uuid.UUID:
        return self.user.organization_id

    @property
    def email(self) -> str:
        return self.user.email

    def can(self, code: str) -> bool:
        return has_permission(self.permissions, code)

    def require(self, code: str) -> None:
        if not self.can(code):
            raise AuthForbidden(f"Thiếu quyền: {code}")

    def is_admin(self) -> bool:
        return "*" in self.permissions


def _load_principal(db: Session, user: User) -> Principal:
    assignments = db.execute(
        select(RoleAssignment, Role)
        .join(Role, Role.id == RoleAssignment.role_id)
        .where(RoleAssignment.user_id == user.id)
    ).all()
    perms: set[str] = set()
    sys_roles: set[str] = set()
    units: set[uuid.UUID] = set()
    entities: set[tuple[str, uuid.UUID]] = set()
    for ra, role in assignments:
        perms.update(role.permissions or [])
        if role.scope_level == "SYSTEM":
            sys_roles.add(role.code)
        if ra.scope_type == "unit" and ra.scope_id:
            units.add(ra.scope_id)
        elif ra.scope_type and ra.scope_id:
            entities.add((ra.scope_type, ra.scope_id))
    return Principal(
        user=user,
        permissions=perms,
        system_roles=sys_roles,
        unit_scopes=units,
        entity_scopes=entities,
    )


def get_principal(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Principal:
    if creds is None or not creds.credentials:
        raise AuthUnauthorized("Thiếu access token.")
    try:
        payload = decode_token(creds.credentials)
    except Exception as exc:  # noqa: BLE001
        raise AuthUnauthorized("Token không hợp lệ hoặc đã hết hạn.") from exc
    if payload.get("type") != "access":
        raise AuthUnauthorized("Token không hợp lệ.")
    user_id = payload.get("sub")
    user = db.get(User, uuid.UUID(user_id)) if user_id else None
    if user is None or user.status in {"DISABLED", "SUSPENDED"}:
        raise AuthUnauthorized("Tài khoản không tồn tại hoặc bị khóa.")
    principal = _load_principal(db, user)
    request.state.principal_id = str(user.id)
    return principal


def require(*codes: str, mode: str = "any"):
    """Dependency factory enforcing permission codes (mode: any|all)."""

    def _guard(principal: Principal = Depends(get_principal)) -> Principal:
        ok = (
            any(principal.can(c) for c in codes)
            if mode == "any"
            else all(principal.can(c) for c in codes)
        )
        if not ok:
            raise AuthForbidden(f"Thiếu quyền: {', '.join(codes)}")
        return principal

    return _guard


def ensure_org_scope(principal: Principal, organization_id: uuid.UUID) -> None:
    """Object-level guard: principal may only access its own organization."""
    if principal.organization_id != organization_id:
        raise AuthForbidden("Ngoài phạm vi tổ chức.")
