"""Funding program / call schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.common import IdMixin


class ProgramIn(BaseModel):
    code: str
    title: str
    funder_id: uuid.UUID | None = None
    objective: str | None = None
    year_from: int | None = None
    year_to: int | None = None
    budget_ceiling: Decimal | None = None
    currency: str = "VND"


class ProgramOut(IdMixin):
    organization_id: uuid.UUID
    code: str
    title: str
    funder_id: uuid.UUID | None = None
    objective: str | None = None
    year_from: int | None = None
    year_to: int | None = None
    budget_ceiling: Decimal | None = None
    currency: str
    status: str


class CallIn(BaseModel):
    code: str
    title: str
    description: str | None = None
    program_id: uuid.UUID | None = None
    task_level: str = "INSTITUTIONAL"
    open_at: datetime | None = None
    close_at: datetime | None = None
    budget_limit: Decimal | None = None
    currency: str = "VND"
    duration_months: int | None = None
    max_proposals_per_pi: int | None = None
    fields: list[str] = []
    required_documents: list[str] = []


class CallUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    open_at: datetime | None = None
    close_at: datetime | None = None
    budget_limit: Decimal | None = None
    duration_months: int | None = None
    max_proposals_per_pi: int | None = None
    fields: list[str] | None = None
    required_documents: list[str] | None = None


class EligibilityRuleIn(BaseModel):
    rule_type: str
    expression_json: dict = {}
    message_vi: str
    message_en: str | None = None
    severity: str = "ERROR"


class CallOut(IdMixin):
    organization_id: uuid.UUID
    program_id: uuid.UUID | None = None
    code: str
    title: str
    description: str | None = None
    task_level: str
    open_at: datetime | None = None
    close_at: datetime | None = None
    budget_limit: Decimal | None = None
    currency: str
    duration_months: int | None = None
    max_proposals_per_pi: int | None = None
    fields: list = []
    required_documents: list = []
    status: str
    published_version: int
    published_at: datetime | None = None
