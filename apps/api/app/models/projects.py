"""Project lifecycle: activation, baseline, plan, progress, change, risk, closure."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import BaseModel
from app.core.enums import (
    ChangeStatus,
    ProjectStatus,
    ReportStatus,
    RiskStatus,
    TaskStatus,
)


class Project(BaseModel):
    __tablename__ = "projects"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    proposal_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, index=True
    )
    project_code: Mapped[str] = mapped_column(String(50), index=True)
    title: Mapped[str] = mapped_column(String(500))
    pi_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    lead_unit_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(30), default=ProjectStatus.PENDING_ACTIVATION, index=True
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    approved_budget: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="VND")
    decision_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    contract_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    completion_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    grade: Mapped[str | None] = mapped_column(String(40), nullable=True)


class ProjectBaseline(BaseModel):
    __tablename__ = "project_baselines"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id"), index=True
    )
    baseline_no: Mapped[int] = mapped_column(Integer, default=1)
    scope_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    budget_total: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0)
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_decision_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )


class ProjectMember(BaseModel):
    __tablename__ = "project_members"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id"), index=True
    )
    researcher_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    member_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(40), default="MEMBER")
    unit_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)


class ProjectTask(BaseModel):
    __tablename__ = "project_tasks"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id"), index=True
    )
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    work_package_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    progress_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    status: Mapped[str] = mapped_column(String(20), default=TaskStatus.TODO)
    order_no: Mapped[int] = mapped_column(Integer, default=1)


class ProgressReport(BaseModel):
    __tablename__ = "progress_reports"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id"), index=True
    )
    report_type: Mapped[str] = mapped_column(String(30), default="PERIODIC")
    period_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    completion_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    narrative: Mapped[str | None] = mapped_column(Text, nullable=True)
    metrics_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(30), default=ReportStatus.DRAFT)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ChangeRequest(BaseModel):
    __tablename__ = "change_requests"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id"), index=True
    )
    change_type: Mapped[str] = mapped_column(String(40))  # TIMELINE|BUDGET|SCOPE|TEAM|DELIVERABLE
    before_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    after_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    impact: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=ChangeStatus.DRAFT)
    decision_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)


class Risk(BaseModel):
    __tablename__ = "risks"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id"), index=True
    )
    category: Mapped[str | None] = mapped_column(String(60), nullable=True)
    description: Mapped[str] = mapped_column(Text)
    probability: Mapped[int] = mapped_column(Integer, default=1)  # 1..5
    impact: Mapped[int] = mapped_column(Integer, default=1)  # 1..5
    score: Mapped[int] = mapped_column(Integer, default=1)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    mitigation: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=RiskStatus.OPEN)


class Closure(BaseModel):
    __tablename__ = "closures"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id"), index=True
    )
    result: Mapped[str | None] = mapped_column(String(40), nullable=True)  # grade
    council_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    obligations: Mapped[str | None] = mapped_column(Text, nullable=True)
    lessons_learned: Mapped[str | None] = mapped_column(Text, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FinanceTransaction(BaseModel):
    """Administrative finance view (snapshot/import from ERP). Not the source of truth."""

    __tablename__ = "finance_transactions"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    source_system: Mapped[str] = mapped_column(String(40), default="MANUAL")
    external_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    transaction_type: Mapped[str] = mapped_column(
        String(30)
    )  # BUDGET|COMMITTED|DISBURSED|ACTUAL|SETTLEMENT
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="VND")
    transaction_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
