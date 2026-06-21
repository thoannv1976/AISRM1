"""Ethics & integrity (M11): applications, screening, review, decision.

Restricted data; AI is not used to decide. State machine:
DRAFT → SUBMITTED → SCREENING → UNDER_REVIEW → REVISION → APPROVED/EXEMPT/REJECTED.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api._helpers import apply_updates, get_org_scoped
from app.core.db import get_db
from app.core.deps import Principal, require
from app.core.enums import EthicsStatus
from app.core.errors import InvalidStateTransition
from app.core.pagination import Page, PageParams, build_page, page_params, paginate
from app.models.research_extra import EthicsApplication, EthicsDecision, EthicsReview
from app.schemas.common import IdMixin
from app.services import audit
from app.services.numbering import next_code

router = APIRouter()


class EthicsIn(BaseModel):
    title: str
    project_id: uuid.UUID | None = None
    proposal_id: uuid.UUID | None = None
    review_type: str = "FULL"
    risk_level: str = "MEDIUM"
    involves_human_subjects: bool = False
    involves_sensitive_data: bool = False
    summary: str | None = None
    content_json: dict = {}


class EthicsUpdate(BaseModel):
    title: str | None = None
    review_type: str | None = None
    risk_level: str | None = None
    summary: str | None = None
    content_json: dict | None = None


class EthicsDecisionIn(BaseModel):
    outcome: str  # APPROVED | EXEMPT | REJECTED
    conditions: str | None = None
    valid_months: int = 12


class EthicsOut(IdMixin):
    organization_id: uuid.UUID
    code: str
    title: str
    review_type: str
    risk_level: str
    status: str
    classification: str
    summary: str | None = None
    valid_to: date | None = None


@router.get("", response_model=Page[EthicsOut])
def list_apps(
    status: str | None = None,
    db: Session = Depends(get_db),
    params: PageParams = Depends(page_params),
    principal: Principal = Depends(require("ethics.read")),
) -> Page[EthicsOut]:
    stmt = select(EthicsApplication).where(
        EthicsApplication.organization_id == principal.organization_id
    )
    if status:
        stmt = stmt.where(EthicsApplication.status == status)
    stmt = stmt.order_by(EthicsApplication.created_at.desc())
    items, total = paginate(db, stmt, params)
    return build_page([EthicsOut.model_validate(i) for i in items], total, params)


@router.post("", response_model=EthicsOut, status_code=201)
def create_app(
    payload: EthicsIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("ethics.create", "ethics.update")),
) -> EthicsOut:
    app = EthicsApplication(
        organization_id=principal.organization_id,
        code=next_code(db, EthicsApplication, "ETH", principal.organization_id),
        applicant_id=principal.id,
        status=EthicsStatus.DRAFT,
        **payload.model_dump(),
    )
    db.add(app)
    db.flush()
    audit.record(
        db,
        action="ethics.create",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="ethics",
        entity_id=app.id,
    )
    return EthicsOut.model_validate(app)


@router.get("/{app_id}", response_model=EthicsOut)
def get_app(
    app_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("ethics.read")),
) -> EthicsOut:
    return EthicsOut.model_validate(get_org_scoped(db, EthicsApplication, app_id, principal))


@router.patch("/{app_id}", response_model=EthicsOut)
def update_app(
    app_id: uuid.UUID,
    payload: EthicsUpdate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("ethics.update")),
) -> EthicsOut:
    app = get_org_scoped(db, EthicsApplication, app_id, principal)
    if app.status not in {EthicsStatus.DRAFT, EthicsStatus.REVISION}:
        raise InvalidStateTransition("Chỉ sửa được hồ sơ ở trạng thái nháp/yêu cầu sửa.")
    apply_updates(app, payload.model_dump(exclude_unset=True))
    return EthicsOut.model_validate(app)


@router.post("/{app_id}/submit", response_model=EthicsOut)
def submit_app(
    app_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("ethics.update", "ethics.create")),
) -> EthicsOut:
    app = get_org_scoped(db, EthicsApplication, app_id, principal)
    if app.status not in {EthicsStatus.DRAFT, EthicsStatus.REVISION}:
        raise InvalidStateTransition("Hồ sơ không ở trạng thái có thể nộp.")
    app.status = EthicsStatus.SUBMITTED
    app.submitted_at = datetime.now(tz=UTC)
    audit.record(
        db,
        action="ethics.submit",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="ethics",
        entity_id=app.id,
    )
    return EthicsOut.model_validate(app)


@router.post("/{app_id}/screen", response_model=EthicsOut)
def screen_app(
    app_id: uuid.UUID,
    review_type: str = "FULL",
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("ethics.update", "ethics.decide")),
) -> EthicsOut:
    app = get_org_scoped(db, EthicsApplication, app_id, principal)
    if app.status not in {EthicsStatus.SUBMITTED, EthicsStatus.SCREENING}:
        raise InvalidStateTransition("Chỉ phân loại hồ sơ đã nộp.")
    app.review_type = review_type
    app.status = EthicsStatus.UNDER_REVIEW
    audit.record(
        db,
        action="ethics.screen",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="ethics",
        entity_id=app.id,
        metadata={"review_type": review_type},
    )
    return EthicsOut.model_validate(app)


@router.post("/{app_id}/review", status_code=201)
def add_review(
    app_id: uuid.UUID,
    recommendation: str,
    comment: str | None = None,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("ethics.review", "ethics.update")),
) -> dict:
    app = get_org_scoped(db, EthicsApplication, app_id, principal)
    db.add(
        EthicsReview(
            organization_id=principal.organization_id,
            application_id=app.id,
            reviewer_id=principal.id,
            recommendation=recommendation,
            comment=comment,
            decided_at=datetime.now(tz=UTC),
        )
    )
    return {"ok": True}


@router.post("/{app_id}/decision", response_model=EthicsOut)
def decide_app(
    app_id: uuid.UUID,
    payload: EthicsDecisionIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("ethics.decide")),
) -> EthicsOut:
    app = get_org_scoped(db, EthicsApplication, app_id, principal)
    if app.status not in {EthicsStatus.UNDER_REVIEW, EthicsStatus.SCREENING, EthicsStatus.REVISION}:
        raise InvalidStateTransition("Hồ sơ không ở trạng thái có thể ra quyết định.")
    today = datetime.now(tz=UTC).date()
    valid_until = (
        date(today.year + (payload.valid_months // 12), today.month, today.day)
        if payload.valid_months >= 12
        else today
    )
    db.add(
        EthicsDecision(
            organization_id=principal.organization_id,
            application_id=app.id,
            outcome=payload.outcome,
            conditions=payload.conditions,
            valid_until=valid_until,
            decided_by=principal.id,
            decided_at=datetime.now(tz=UTC),
        )
    )
    app.status = {
        "APPROVED": EthicsStatus.APPROVED,
        "EXEMPT": EthicsStatus.EXEMPT,
        "REJECTED": EthicsStatus.REJECTED,
    }.get(payload.outcome, EthicsStatus.UNDER_REVIEW)
    app.valid_from = today
    app.valid_to = valid_until
    audit.record(
        db,
        action="ethics.decision",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="ethics",
        entity_id=app.id,
        metadata={"outcome": payload.outcome},
    )
    return EthicsOut.model_validate(app)
