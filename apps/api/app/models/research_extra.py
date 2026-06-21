"""Ethics/integrity (M11) and KPI/reward (M12) models."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import BaseModel
from app.core.enums import (
    Classification,
    EthicsReviewType,
    EthicsStatus,
    KPIRunStatus,
    RewardStatus,
)


# ----- Ethics -----
class EthicsApplication(BaseModel):
    __tablename__ = "ethics_applications"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_ethics_code"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    code: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(500))
    project_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    proposal_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    applicant_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    review_type: Mapped[str] = mapped_column(String(20), default=EthicsReviewType.FULL)
    risk_level: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    involves_human_subjects: Mapped[bool] = mapped_column(default=False)
    involves_sensitive_data: Mapped[bool] = mapped_column(default=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    classification: Mapped[str] = mapped_column(String(20), default=Classification.RESTRICTED)
    status: Mapped[str] = mapped_column(String(20), default=EthicsStatus.DRAFT, index=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EthicsReview(BaseModel):
    __tablename__ = "ethics_reviews"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    application_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("ethics_applications.id"), index=True
    )
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    recommendation: Mapped[str | None] = mapped_column(String(30), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EthicsDecision(BaseModel):
    __tablename__ = "ethics_decisions"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    application_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("ethics_applications.id"), index=True
    )
    outcome: Mapped[str] = mapped_column(String(20))  # APPROVED|EXEMPT|REJECTED
    conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ----- KPI -----
class KPIRuleVersion(BaseModel):
    __tablename__ = "kpi_rule_versions"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    code: Mapped[str] = mapped_column(String(50))
    version_no: Mapped[int] = mapped_column(Integer, default=1)
    expression_json: Mapped[dict] = mapped_column(JSONB, default=dict)  # points per output_type
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)


class KPIRun(BaseModel):
    __tablename__ = "kpi_runs"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    period: Mapped[str] = mapped_column(String(20))  # e.g. 2026
    rule_version_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    rule_hash: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=KPIRunStatus.DRAFT)
    total_points: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class KPIContribution(BaseModel):
    __tablename__ = "kpi_contributions"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    run_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("kpi_runs.id"), index=True
    )
    researcher_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    researcher_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    output_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    points: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=0)
    detail_json: Mapped[dict] = mapped_column(JSONB, default=dict)


class RewardApplication(BaseModel):
    __tablename__ = "reward_applications"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_reward_code"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    code: Mapped[str] = mapped_column(String(50))
    applicant_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    output_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    title: Mapped[str] = mapped_column(String(500))
    points: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=0)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="VND")
    status: Mapped[str] = mapped_column(String(20), default=RewardStatus.DRAFT, index=True)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
