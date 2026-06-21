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


class FeatureToggleIn(BaseModel):
    enabled: bool


class AIConfigOut(BaseModel):
    mode: str
    provider: str
    llm_model: str
    embedding_model: str
    monthly_budget: float
    currency: str
    api_key_masked: str | None = None
    api_key_source: str  # DB | ENV | NONE
    effective_provider: str
    effective_label: str
    effective_model: str
    available_models: list[str]
    last_test_at: str | None = None
    last_test_ok: bool | None = None
    last_test_message: str | None = None


class AIConfigIn(BaseModel):
    mode: str | None = None  # AUTO | CLAUDE | MOCK
    provider: str | None = None  # anthropic | vertex_ai
    llm_model: str | None = None
    monthly_budget: float | None = None
    api_key: str | None = None  # empty/None = keep current
    clear_key: bool = False


class AITestOut(BaseModel):
    ok: bool
    message: str
    latency_ms: int
    provider: str
    model: str


class AIUsageOut(BaseModel):
    calls: int
    jobs: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    estimated_cost: float
    currency: str
    monthly_budget: float
