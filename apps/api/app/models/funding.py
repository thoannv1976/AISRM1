"""Funding sources, programs, calls, eligibility rules and form templates."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import BaseModel
from app.core.enums import CallStatus


class FundingSource(BaseModel):
    __tablename__ = "funding_sources"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_source_org_code"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    code: Mapped[str] = mapped_column(String(50))
    name_vi: Mapped[str] = mapped_column(String(255))
    name_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_type: Mapped[str] = mapped_column(
        String(40), default="INTERNAL"
    )  # INTERNAL|MINISTRY|PROVINCE|FUND|ENTERPRISE|INTERNATIONAL
    funder_name: Mapped[str | None] = mapped_column(String(255), nullable=True)


class FundingProgram(BaseModel):
    __tablename__ = "funding_programs"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_program_org_code"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    code: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(500))
    funder_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("funding_sources.id"), nullable=True
    )
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    year_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    year_to: Mapped[int | None] = mapped_column(Integer, nullable=True)
    budget_ceiling: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="VND")
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")


class FundingCall(BaseModel):
    """Call for proposals. Eligibility/form/deadline immutable after open via version."""

    __tablename__ = "funding_calls"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_call_org_code"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    program_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("funding_programs.id"), nullable=True, index=True
    )
    code: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_level: Mapped[str] = mapped_column(String(40), default="INSTITUTIONAL")  # cấp đề tài
    open_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    close_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Ho_Chi_Minh")
    budget_limit: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="VND")
    max_proposals_per_pi: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fields: Mapped[list] = mapped_column(JSONB, default=list)
    required_documents: Mapped[list] = mapped_column(JSONB, default=list)
    workflow_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(20), default=CallStatus.DRAFT)
    published_version: Mapped[int] = mapped_column(Integer, default=0)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EligibilityRule(BaseModel):
    """Sandboxed eligibility rule (declarative; evaluated by the rule engine)."""

    __tablename__ = "eligibility_rules"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    call_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("funding_calls.id"), index=True
    )
    rule_type: Mapped[str] = mapped_column(String(40))  # e.g. MAX_BUDGET, REQUIRE_FIELD, PI_DEGREE
    expression_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    message_vi: Mapped[str] = mapped_column(String(500))
    message_en: Mapped[str | None] = mapped_column(String(500), nullable=True)
    severity: Mapped[str] = mapped_column(String(10), default="ERROR")  # ERROR|WARNING


class FormTemplate(BaseModel):
    """Versioned proposal/review form built from controlled components."""

    __tablename__ = "form_templates"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(255))
    form_type: Mapped[str] = mapped_column(String(30), default="PROPOSAL")  # PROPOSAL|REVIEW|REPORT
    version_no: Mapped[int] = mapped_column(Integer, default=1)
    schema_json: Mapped[dict] = mapped_column(JSONB, default=dict)  # sections + fields
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
