"""AI governance: providers, features, prompts, jobs, outputs, citations, usage."""

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
from app.core.enums import AIJobStatus, AIOutputStatus


class AIFeature(BaseModel):
    """A configurable AI feature (AI-01..AI-25) with risk level and flags."""

    __tablename__ = "ai_features"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_ai_feature_code"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_level: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_citations: Mapped[bool] = mapped_column(Boolean, default=True)
    allowed_classifications: Mapped[list] = mapped_column(JSONB, default=list)
    default_model: Mapped[str | None] = mapped_column(String(80), nullable=True)


class AIPromptTemplate(BaseModel):
    __tablename__ = "ai_prompt_templates"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    feature_code: Mapped[str] = mapped_column(String(50), index=True)
    version_no: Mapped[int] = mapped_column(Integer, default=1)
    system_prompt: Mapped[str] = mapped_column(Text)
    user_template: Mapped[str] = mapped_column(Text)
    output_schema: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AIJob(BaseModel):
    __tablename__ = "ai_jobs"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    feature_code: Mapped[str] = mapped_column(String(50), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    requester_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    language: Mapped[str] = mapped_column(String(5), default="vi")
    model_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(40), nullable=True)
    prompt_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    input_hash: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    options: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(20), default=AIJobStatus.QUEUED, index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AIOutput(BaseModel):
    """AI result — always a DRAFT/suggestion requiring human review."""

    __tablename__ = "ai_outputs"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    job_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("ai_jobs.id"), index=True
    )
    output_type: Mapped[str] = mapped_column(String(40), default="SUMMARY")
    content_json: Mapped[dict] = mapped_column(JSONB, default=dict)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)
    insufficient_evidence: Mapped[bool] = mapped_column(Boolean, default=False)
    human_status: Mapped[str] = mapped_column(String(20), default=AIOutputStatus.DRAFT)
    accepted_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stale_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AICitation(BaseModel):
    __tablename__ = "ai_citations"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    output_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("ai_outputs.id"), index=True
    )
    citation_id: Mapped[str] = mapped_column(String(40))  # referenced in content findings
    document_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    document_version_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    chunk_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    relevance_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3), nullable=True)


class AIFeedback(BaseModel):
    __tablename__ = "ai_feedback"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    output_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    rating: Mapped[str | None] = mapped_column(String(10), nullable=True)  # UP|DOWN
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reported: Mapped[bool] = mapped_column(Boolean, default=False)


class AIUsageLedger(BaseModel):
    __tablename__ = "ai_usage_ledger"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    job_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    feature_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
