"""Analytics: report definitions/runs/snapshots and KPI definitions."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import BaseModel


class ReportDefinition(BaseModel):
    __tablename__ = "report_definitions"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_report_code"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    code: Mapped[str] = mapped_column(String(20))  # R01..R28
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(60), nullable=True)
    output_formats: Mapped[list] = mapped_column(JSONB, default=list)  # [EXCEL, PDF, WORD]
    metrics_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ReportRun(BaseModel):
    __tablename__ = "report_runs"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    report_code: Mapped[str] = mapped_column(String(20), index=True)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    params_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    snapshot_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    snapshot_hash: Mapped[str | None] = mapped_column(String(80), nullable=True)
    narrative: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)


class KPIDefinition(BaseModel):
    __tablename__ = "kpi_definitions"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(255))
    version_no: Mapped[int] = mapped_column(Integer, default=1)
    formula_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class CatalogItem(BaseModel):
    """Generic dictionary/catalog item (fields, output types, statuses, SDG...)."""

    __tablename__ = "catalog_items"
    __table_args__ = (UniqueConstraint("organization_id", "category", "code", name="uq_catalog"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    category: Mapped[str] = mapped_column(String(40), index=True)
    code: Mapped[str] = mapped_column(String(60))
    name_vi: Mapped[str] = mapped_column(String(255))
    name_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    parent_code: Mapped[str | None] = mapped_column(String(60), nullable=True)
    order_no: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)
