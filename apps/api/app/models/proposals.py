"""Proposal workspace: proposals, versions, team, workplan, budget, submissions."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
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
from app.core.enums import ProposalStatus


class Proposal(BaseModel):
    """One live record; immutable versions are created at submission."""

    __tablename__ = "proposals"
    __table_args__ = (
        UniqueConstraint("organization_id", "proposal_code", name="uq_proposal_code"),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    call_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("funding_calls.id"), index=True
    )
    proposal_code: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(500))
    title_en: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pi_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    lead_unit_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default=ProposalStatus.DRAFT, index=True)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    fields: Mapped[list] = mapped_column(JSONB, default=list)
    sdgs: Mapped[list] = mapped_column(JSONB, default=list)
    keywords: Mapped[list] = mapped_column(JSONB, default=list)
    content_json: Mapped[dict] = mapped_column(
        JSONB, default=dict
    )  # objectives, methods, data, ethics...
    duration_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    budget_total: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="VND")
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProposalVersion(BaseModel):
    """Immutable snapshot created at submission (or internal milestone)."""

    __tablename__ = "proposal_versions"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("proposals.id"), index=True
    )
    version_no: Mapped[int] = mapped_column(Integer, default=1)
    content_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    budget_total: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    snapshot_hash: Mapped[str | None] = mapped_column(String(80), nullable=True)
    is_immutable: Mapped[bool] = mapped_column(Boolean, default=False)


class ProposalTeamMember(BaseModel):
    __tablename__ = "proposal_team_members"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("proposals.id"), index=True
    )
    researcher_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    external_person_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(40), default="MEMBER")  # PI|CO_PI|MEMBER|ADVISOR
    contribution_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    unit_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    tasks_summary: Mapped[str | None] = mapped_column(Text, nullable=True)


class WorkPackage(BaseModel):
    __tablename__ = "work_packages"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    proposal_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, index=True
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, index=True
    )
    code: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(500))
    lead_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    objectives: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    order_no: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="PLANNED")


class Milestone(BaseModel):
    __tablename__ = "milestones"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    proposal_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, index=True
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, index=True
    )
    code: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(500))
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    order_no: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="PLANNED")


class Deliverable(BaseModel):
    __tablename__ = "deliverables"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    proposal_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, index=True
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, index=True
    )
    code: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(500))
    deliverable_type: Mapped[str] = mapped_column(String(40), default="REPORT")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    acceptance_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="PLANNED")


class ProposalBudgetLine(BaseModel):
    __tablename__ = "proposal_budget_lines"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("proposals.id"), index=True
    )
    category: Mapped[str] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="VND")
    funding_source_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)


class Submission(BaseModel):
    """A formal submission event (receipt + snapshot reference)."""

    __tablename__ = "submissions"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("proposals.id"), index=True
    )
    version_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    submitted_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    snapshot_hash: Mapped[str | None] = mapped_column(String(80), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    receipt_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
