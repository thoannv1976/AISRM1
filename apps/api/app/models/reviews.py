"""Review, conflict-of-interest, council and decision models."""

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
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import BaseModel
from app.core.enums import AssignmentStatus, ConflictDecision


class ReviewerProfile(BaseModel):
    """Reviewer pool entry (internal or external expert)."""

    __tablename__ = "reviewer_profiles"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    affiliation: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country: Mapped[str | None] = mapped_column(String(80), nullable=True)
    expertise: Mapped[list] = mapped_column(JSONB, default=list)
    languages: Mapped[list] = mapped_column(JSONB, default=list)
    current_load: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_external: Mapped[bool] = mapped_column(Boolean, default=False)


class ConflictDeclaration(BaseModel):
    __tablename__ = "conflict_declarations"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    reviewer_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    proposal_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, index=True
    )
    conflict_type: Mapped[str] = mapped_column(String(30))
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision: Mapped[str] = mapped_column(String(20), default=ConflictDecision.DECLARED)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)


class ReviewTemplate(BaseModel):
    __tablename__ = "review_templates"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(255))
    blind_mode: Mapped[str] = mapped_column(
        String(20), default="SINGLE_BLIND"
    )  # OPEN|SINGLE_BLIND|DOUBLE_BLIND
    criteria: Mapped[list] = mapped_column(JSONB, default=list)  # [{code,name,weight,max_score}]
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ReviewAssignment(BaseModel):
    __tablename__ = "review_assignments"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    proposal_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("proposals.id"), index=True
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    template_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    review_round: Mapped[int] = mapped_column(Integer, default=1)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=AssignmentStatus.INVITED)
    blind_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    coi_checked: Mapped[bool] = mapped_column(Boolean, default=False)
    confidentiality_accepted: Mapped[bool] = mapped_column(Boolean, default=False)


class Review(BaseModel):
    __tablename__ = "reviews"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("review_assignments.id"), index=True
    )
    proposal_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    overall_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    recommendation: Mapped[str | None] = mapped_column(String(20), nullable=True)
    applicant_comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidential_comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    strengths: Mapped[str | None] = mapped_column(Text, nullable=True)
    weaknesses: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ReviewScore(BaseModel):
    __tablename__ = "review_scores"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    review_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("reviews.id"), index=True
    )
    criterion_code: Mapped[str] = mapped_column(String(50))
    score: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=0)
    weight: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=1)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)


class Council(BaseModel):
    __tablename__ = "councils"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(255))
    council_type: Mapped[str] = mapped_column(
        String(30), default="SELECTION"
    )  # SELECTION|ACCEPTANCE|ETHICS
    scope_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    scope_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    chair_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    secretary_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")


class CouncilMember(BaseModel):
    __tablename__ = "council_members"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    council_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("councils.id"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    member_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(
        String(30), default="MEMBER"
    )  # CHAIR|SECRETARY|MEMBER|REVIEWER


class CouncilMeeting(BaseModel):
    __tablename__ = "council_meetings"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    council_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("councils.id"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    meeting_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    online_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    quorum_required: Mapped[int] = mapped_column(Integer, default=0)
    agenda: Mapped[list] = mapped_column(JSONB, default=list)
    minutes_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="SCHEDULED")  # SCHEDULED|FINALIZED


class Vote(BaseModel):
    __tablename__ = "votes"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("council_meetings.id"), index=True
    )
    proposal_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    member_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    vote_value: Mapped[str] = mapped_column(String(20))  # APPROVE|REJECT|ABSTAIN
    score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)


class Decision(BaseModel):
    """Official decision (selection / acceptance). Made by authorized humans only."""

    __tablename__ = "decisions"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    scope_type: Mapped[str] = mapped_column(String(30))  # proposal|project|deliverable
    scope_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    decision_type: Mapped[str] = mapped_column(String(40), default="FUNDING")
    decision_no: Mapped[str | None] = mapped_column(String(50), nullable=True)
    decision_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    outcome: Mapped[str] = mapped_column(String(30))
    conditions: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_budget: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    signed_document_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
