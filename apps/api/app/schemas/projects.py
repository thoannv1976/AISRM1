"""Project lifecycle schemas."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.schemas.common import IdMixin


class ProjectCreate(BaseModel):
    project_code: str | None = None
    title: str
    pi_id: uuid.UUID
    lead_unit_id: uuid.UUID | None = None
    start_date: date | None = None
    end_date: date | None = None
    approved_budget: Decimal = Decimal(0)
    currency: str = "VND"
    contract_no: str | None = None


class ProjectUpdate(BaseModel):
    title: str | None = None
    lead_unit_id: uuid.UUID | None = None
    start_date: date | None = None
    end_date: date | None = None
    completion_percent: Decimal | None = None
    contract_no: str | None = None
    version: int | None = None


class ProjectOut(IdMixin):
    organization_id: uuid.UUID
    proposal_id: uuid.UUID | None = None
    project_code: str
    title: str
    pi_id: uuid.UUID
    lead_unit_id: uuid.UUID | None = None
    status: str
    start_date: date | None = None
    end_date: date | None = None
    approved_budget: Decimal
    currency: str
    completion_percent: Decimal
    grade: str | None = None
    version: int


class TaskIn(BaseModel):
    title: str
    description: str | None = None
    assignee_id: uuid.UUID | None = None
    work_package_id: uuid.UUID | None = None
    due_date: date | None = None
    status: str = "TODO"
    progress_percent: Decimal = Decimal(0)


class TaskOut(IdMixin):
    project_id: uuid.UUID
    title: str
    assignee_id: uuid.UUID | None = None
    due_date: date | None = None
    progress_percent: Decimal
    status: str


class ProgressReportIn(BaseModel):
    report_type: str = "PERIODIC"
    period_from: date | None = None
    period_to: date | None = None
    completion_percent: Decimal = Decimal(0)
    narrative: str | None = None
    metrics_json: dict = {}


class ChangeRequestIn(BaseModel):
    change_type: str
    before_json: dict = {}
    after_json: dict = {}
    justification: str | None = None
    impact: str | None = None


class RiskIn(BaseModel):
    description: str
    category: str | None = None
    probability: int = 1
    impact: int = 1
    owner_id: uuid.UUID | None = None
    mitigation: str | None = None


class FinanceTxnIn(BaseModel):
    transaction_type: str
    amount: Decimal
    currency: str = "VND"
    transaction_date: date | None = None
    source_system: str = "MANUAL"
    external_id: str | None = None
    note: str | None = None


class ClosureIn(BaseModel):
    result: str | None = None
    obligations: str | None = None
    lessons_learned: str | None = None


class TransitionIn(BaseModel):
    target_status: str
    reason: str | None = None
