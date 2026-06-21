"""Review & council schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.common import IdMixin


class ReviewerIn(BaseModel):
    full_name: str
    email: str | None = None
    user_id: uuid.UUID | None = None
    affiliation: str | None = None
    country: str | None = None
    expertise: list[str] = []
    languages: list[str] = []
    is_external: bool = False


class ReviewerOut(IdMixin):
    organization_id: uuid.UUID
    full_name: str
    email: str | None = None
    affiliation: str | None = None
    expertise: list = []
    current_load: int
    is_active: bool
    is_external: bool


class ConflictIn(BaseModel):
    reviewer_id: uuid.UUID
    proposal_id: uuid.UUID | None = None
    conflict_type: str
    details: str | None = None
    decision: str = "DECLARED"


class AssignIn(BaseModel):
    proposal_id: uuid.UUID
    reviewer_id: uuid.UUID
    template_id: uuid.UUID | None = None
    due_at: datetime | None = None


class AcceptIn(BaseModel):
    accept: bool = True
    confidentiality_accepted: bool = True
    coi_declared: bool = False


class ScoreIn(BaseModel):
    criterion_code: str
    score: Decimal
    weight: Decimal = Decimal(1)
    comment: str | None = None


class ReviewSubmitIn(BaseModel):
    recommendation: str
    applicant_comments: str | None = None
    confidential_comments: str | None = None
    strengths: str | None = None
    weaknesses: str | None = None
    scores: list[ScoreIn] = []


class AssignmentOut(IdMixin):
    organization_id: uuid.UUID
    proposal_id: uuid.UUID
    reviewer_id: uuid.UUID
    review_round: int
    status: str
    due_at: datetime | None = None
    coi_checked: bool
    confidentiality_accepted: bool


class ReviewOut(IdMixin):
    organization_id: uuid.UUID
    assignment_id: uuid.UUID
    proposal_id: uuid.UUID
    overall_score: Decimal | None = None
    recommendation: str | None = None
    applicant_comments: str | None = None
    strengths: str | None = None
    weaknesses: str | None = None
    submitted_at: datetime | None = None


class CouncilIn(BaseModel):
    code: str
    name: str
    council_type: str = "SELECTION"
    chair_id: uuid.UUID | None = None
    secretary_id: uuid.UUID | None = None
    scope_type: str | None = None
    scope_id: uuid.UUID | None = None


class CouncilOut(IdMixin):
    organization_id: uuid.UUID
    code: str
    name: str
    council_type: str
    chair_id: uuid.UUID | None = None
    secretary_id: uuid.UUID | None = None
    status: str


class MeetingIn(BaseModel):
    title: str
    meeting_at: datetime | None = None
    location: str | None = None
    online_url: str | None = None
    quorum_required: int = 0
    agenda: list = []


class SuggestionOut(BaseModel):
    reviewer_id: uuid.UUID
    full_name: str
    score: float
    reasons: list[str]
    excluded: bool = False
    exclusion_reason: str | None = None
