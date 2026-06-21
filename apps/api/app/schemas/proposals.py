"""Proposal schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.common import IdMixin


class ProposalCreate(BaseModel):
    call_id: uuid.UUID
    title: str
    title_en: str | None = None
    abstract: str | None = None
    pi_id: uuid.UUID | None = None  # defaults to current user's researcher profile
    lead_unit_id: uuid.UUID | None = None
    duration_months: int | None = None
    fields: list[str] = []
    sdgs: list[str] = []
    keywords: list[str] = []


class ProposalUpdate(BaseModel):
    title: str | None = None
    title_en: str | None = None
    abstract: str | None = None
    lead_unit_id: uuid.UUID | None = None
    duration_months: int | None = None
    start_date: date | None = None
    fields: list[str] | None = None
    sdgs: list[str] | None = None
    keywords: list[str] | None = None
    content_json: dict | None = None
    version: int | None = None  # optimistic concurrency


class TeamMemberIn(BaseModel):
    researcher_id: uuid.UUID | None = None
    external_person_name: str | None = None
    role: str = "MEMBER"
    contribution_percent: Decimal | None = None
    unit_id: uuid.UUID | None = None
    tasks_summary: str | None = None


class WorkPackageIn(BaseModel):
    code: str
    title: str
    lead_id: uuid.UUID | None = None
    objectives: str | None = None
    start_month: int | None = None
    end_month: int | None = None
    order_no: int = 1


class MilestoneIn(BaseModel):
    code: str
    title: str
    due_date: date | None = None
    order_no: int = 1


class DeliverableIn(BaseModel):
    code: str
    title: str
    deliverable_type: str = "REPORT"
    due_date: date | None = None
    acceptance_criteria: str | None = None
    target_value: str | None = None


class BudgetLineIn(BaseModel):
    category: str
    description: str | None = None
    year: int | None = None
    amount: Decimal = Decimal(0)
    currency: str = "VND"
    funding_source_id: uuid.UUID | None = None


class SubmitIn(BaseModel):
    declaration_accepted: bool = True
    confirm_team_consent: bool = True
    submission_note: str | None = None


class DecisionIn(BaseModel):
    outcome: str  # APPROVED|APPROVED_WITH_CONDITIONS|REJECTED|DEFERRED
    decision_no: str | None = None
    conditions: str | None = None
    approved_budget: Decimal | None = None


class ProposalOut(IdMixin):
    organization_id: uuid.UUID
    call_id: uuid.UUID
    proposal_code: str
    title: str
    title_en: str | None = None
    abstract: str | None = None
    pi_id: uuid.UUID
    lead_unit_id: uuid.UUID | None = None
    status: str
    fields: list = []
    sdgs: list = []
    keywords: list = []
    content_json: dict = {}
    duration_months: int | None = None
    budget_total: Decimal
    currency: str
    submitted_at: datetime | None = None
    version: int


class ValidationIssue(BaseModel):
    code: str
    severity: str
    message: str
    field: str | None = None


class ValidationOut(BaseModel):
    ok: bool
    issues: list[ValidationIssue]
