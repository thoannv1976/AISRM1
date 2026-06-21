"""Identity, RBAC and audit models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import BaseModel
from app.core.enums import UserStatus


class Organization(BaseModel):
    __tablename__ = "organizations"

    code: Mapped[str] = mapped_column(String(50), unique=True)
    name_vi: Mapped[str] = mapped_column(String(255))
    name_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    short_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    default_locale: Mapped[str] = mapped_column(String(10), default="vi")
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Ho_Chi_Minh")
    settings_json: Mapped[dict] = mapped_column(JSONB, default=dict)


class User(BaseModel):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("organization_id", "email", name="uq_user_org_email"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )
    email: Mapped[str] = mapped_column(String(255), index=True)
    display_name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=UserStatus.ACTIVE)
    locale: Mapped[str] = mapped_column(String(10), default="vi")
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Ho_Chi_Minh")
    is_external: Mapped[bool] = mapped_column(Boolean, default=False)
    primary_unit_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    title: Mapped[str | None] = mapped_column(String(100), nullable=True)  # học hàm/học vị
    employee_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)


class Role(BaseModel):
    """A named role (system/unit/profile) with a set of permission codes."""

    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_role_org_code"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    code: Mapped[str] = mapped_column(String(50))
    name_vi: Mapped[str] = mapped_column(String(150))
    name_en: Mapped[str | None] = mapped_column(String(150), nullable=True)
    scope_level: Mapped[str] = mapped_column(String(20), default="SYSTEM")  # SYSTEM|UNIT|PROFILE
    permissions: Mapped[list] = mapped_column(JSONB, default=list)  # list[str] permission codes
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)


class RoleAssignment(BaseModel):
    """Assigns a role to a user, optionally scoped to a unit/entity."""

    __tablename__ = "role_assignments"
    __table_args__ = (
        Index("ix_role_assignment_user", "user_id"),
        Index("ix_role_assignment_scope", "scope_type", "scope_id"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    role_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("roles.id"))
    scope_type: Mapped[str | None] = mapped_column(
        String(30), nullable=True
    )  # unit|call|proposal|project
    scope_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class Delegation(BaseModel):
    """Temporary delegation of authority (cannot escalate above delegator)."""

    __tablename__ = "delegations"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    from_user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True))
    to_user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True))
    role_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    scope_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    scope_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    effective_to: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str] = mapped_column(Text)


class Session(BaseModel):
    __tablename__ = "sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    refresh_jti: Mapped[str] = mapped_column(String(64), index=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AuditLog(BaseModel):
    """Append-only audit trail. Never updated by users."""

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_entity", "entity_type", "entity_id"),
        Index("ix_audit_actor", "actor_id"),
        Index("ix_audit_occurred", "occurred_at"),
    )

    organization_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    actor_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action: Mapped[str] = mapped_column(String(80))  # e.g. proposal.submit
    entity_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
