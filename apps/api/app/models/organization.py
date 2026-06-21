"""Organization structure: units (tree + history) and research groups."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import BaseModel
from app.core.enums import UnitType


class OrganizationUnit(BaseModel):
    """Faculty / institute / department / center / office — a tree with history."""

    __tablename__ = "organization_units"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_unit_org_code"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("organization_units.id"), nullable=True
    )
    code: Mapped[str] = mapped_column(String(50))
    name_vi: Mapped[str] = mapped_column(String(255))
    name_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    unit_type: Mapped[str] = mapped_column(String(30), default=UnitType.FACULTY)
    head_user_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    coordinator_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class ResearchGroup(BaseModel):
    __tablename__ = "research_groups"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_group_org_code"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    unit_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    code: Mapped[str] = mapped_column(String(50))
    name_vi: Mapped[str] = mapped_column(String(255))
    name_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lead_user_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    research_areas: Mapped[list] = mapped_column(JSONB, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
