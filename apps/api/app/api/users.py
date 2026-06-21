"""User & role-assignment administration."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api._helpers import apply_updates, get_org_scoped
from app.core.db import get_db
from app.core.deps import Principal, require
from app.core.errors import NotFound, ValidationFailed
from app.core.pagination import Page, PageParams, build_page, page_params, paginate
from app.core.security import hash_password
from app.models.identity import Role, RoleAssignment, User
from app.schemas.auth import RoleAssignIn, UserCreate, UserOut, UserUpdate
from app.services import audit

router = APIRouter()


@router.get("", response_model=Page[UserOut])
def list_users(
    q: str | None = None,
    db: Session = Depends(get_db),
    params: PageParams = Depends(page_params),
    principal: Principal = Depends(require("users.read")),
) -> Page[UserOut]:
    stmt = select(User).where(User.organization_id == principal.organization_id)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where((User.email.ilike(like)) | (User.display_name.ilike(like)))
    stmt = stmt.order_by(User.display_name)
    items, total = paginate(db, stmt, params)
    return build_page([UserOut.model_validate(i) for i in items], total, params)


@router.post("", response_model=UserOut, status_code=201)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("users.create")),
) -> UserOut:
    existing = db.scalar(
        select(User).where(
            User.organization_id == principal.organization_id,
            User.email == payload.email.lower(),
        )
    )
    if existing:
        raise ValidationFailed("Email đã tồn tại trong tổ chức.")
    user = User(
        organization_id=principal.organization_id,
        email=payload.email.lower(),
        display_name=payload.display_name,
        password_hash=hash_password(payload.password) if payload.password else None,
        title=payload.title,
        primary_unit_id=payload.primary_unit_id,
        employee_code=payload.employee_code,
        created_by=principal.id,
    )
    db.add(user)
    db.flush()
    for role_code in payload.roles:
        role = db.scalar(
            select(Role).where(
                Role.organization_id == principal.organization_id, Role.code == role_code
            )
        )
        if role:
            db.add(
                RoleAssignment(
                    organization_id=principal.organization_id, user_id=user.id, role_id=role.id
                )
            )
    audit.record(
        db,
        action="user.create",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="user",
        entity_id=user.id,
    )
    return UserOut.model_validate(user)


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("users.read")),
) -> UserOut:
    return UserOut.model_validate(get_org_scoped(db, User, user_id, principal))


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("users.update")),
) -> UserOut:
    user = get_org_scoped(db, User, user_id, principal)
    apply_updates(user, payload.model_dump(exclude_unset=True))
    audit.record(
        db,
        action="user.update",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="user",
        entity_id=user.id,
    )
    return UserOut.model_validate(user)


@router.post("/role-assignments", status_code=201)
def assign_role(
    payload: RoleAssignIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("users.update", "admin.config")),
) -> dict:
    user = get_org_scoped(db, User, payload.user_id, principal)
    role = db.scalar(
        select(Role).where(
            Role.organization_id == principal.organization_id, Role.code == payload.role_code
        )
    )
    if not role:
        raise NotFound("Vai trò không tồn tại.")
    db.add(
        RoleAssignment(
            organization_id=principal.organization_id,
            user_id=user.id,
            role_id=role.id,
            scope_type=payload.scope_type,
            scope_id=payload.scope_id,
            reason=payload.reason,
        )
    )
    audit.record(
        db,
        action="user.role.assign",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="user",
        entity_id=user.id,
        metadata={"role": payload.role_code, "scope": payload.scope_type},
    )
    return {"ok": True}
