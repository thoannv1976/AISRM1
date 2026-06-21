"""AI Copilot schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.common import IdMixin


class AIJobCreate(BaseModel):
    feature_code: str
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    language: str = "vi"
    options: dict = {}


class AIJobOut(IdMixin):
    organization_id: uuid.UUID
    feature_code: str
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    status: str
    model_id: str | None = None
    provider: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class CitationOut(BaseModel):
    citation_id: str
    document_id: uuid.UUID | None = None
    excerpt: str | None = None
    relevance_score: Decimal | None = None


class AIOutputOut(IdMixin):
    job_id: uuid.UUID
    output_type: str
    content_json: dict
    confidence: Decimal | None = None
    insufficient_evidence: bool
    human_status: str
    citations: list[CitationOut] = []


class FeedbackIn(BaseModel):
    rating: str | None = None  # UP|DOWN
    reason: str | None = None
    report: bool = False
    accept: bool | None = None  # accept/reject the suggestion


class ChatIn(BaseModel):
    message: str
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    language: str = "vi"


class ChatOut(BaseModel):
    answer: str
    citations: list[CitationOut] = []
    insufficient_evidence: bool = False


class FeatureOut(IdMixin):
    code: str
    name: str
    description: str | None = None
    risk_level: str
    enabled: bool
    requires_citations: bool
