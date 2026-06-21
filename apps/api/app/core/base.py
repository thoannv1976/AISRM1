"""Declarative base and common model mixins."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)


class VersionMixin:
    """Optimistic-concurrency version counter."""

    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OrgScopedMixin:
    """Most business tables are scoped to an organization (multi-tenant ready)."""

    organization_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), index=True, nullable=False
    )


class BaseModel(Base, TimestampMixin, VersionMixin):
    """Convenience base: UUID pk + timestamps + version."""

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


class OrgModel(BaseModel, OrgScopedMixin):
    """Org-scoped base model."""

    __abstract__ = True


# Re-export a commonly used column type
def str_col(length: int = 255, **kw) -> Mapped[str]:
    return mapped_column(String(length), **kw)
