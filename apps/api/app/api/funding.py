"""Funding programs and calls for proposals."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api._helpers import apply_updates, get_org_scoped
from app.core.db import get_db
from app.core.deps import Principal, require
from app.core.enums import CallStatus
from app.core.errors import InvalidStateTransition
from app.core.pagination import Page, PageParams, build_page, page_params, paginate
from app.models.funding import EligibilityRule, FundingCall, FundingProgram
from app.schemas.funding import (
    CallIn,
    CallOut,
    CallUpdate,
    EligibilityRuleIn,
    ProgramIn,
    ProgramOut,
)
from app.services import audit

router = APIRouter()


# ----- Programs -----
@router.get("/funding-programs", response_model=Page[ProgramOut])
def list_programs(
    db: Session = Depends(get_db),
    params: PageParams = Depends(page_params),
    principal: Principal = Depends(require("funding.read")),
) -> Page[ProgramOut]:
    stmt = (
        select(FundingProgram)
        .where(FundingProgram.organization_id == principal.organization_id)
        .order_by(FundingProgram.code)
    )
    items, total = paginate(db, stmt, params)
    return build_page([ProgramOut.model_validate(i) for i in items], total, params)


@router.post("/funding-programs", response_model=ProgramOut, status_code=201)
def create_program(
    payload: ProgramIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("funding.create")),
) -> ProgramOut:
    program = FundingProgram(
        organization_id=principal.organization_id, created_by=principal.id, **payload.model_dump()
    )
    db.add(program)
    db.flush()
    audit.record(
        db,
        action="program.create",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="program",
        entity_id=program.id,
    )
    return ProgramOut.model_validate(program)


# ----- Calls -----
@router.get("/funding-calls", response_model=Page[CallOut])
def list_calls(
    status: str | None = None,
    db: Session = Depends(get_db),
    params: PageParams = Depends(page_params),
    principal: Principal = Depends(require("calls.read")),
) -> Page[CallOut]:
    stmt = select(FundingCall).where(FundingCall.organization_id == principal.organization_id)
    if status:
        stmt = stmt.where(FundingCall.status == status)
    stmt = stmt.order_by(FundingCall.created_at.desc())
    items, total = paginate(db, stmt, params)
    return build_page([CallOut.model_validate(i) for i in items], total, params)


@router.post("/funding-calls", response_model=CallOut, status_code=201)
def create_call(
    payload: CallIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("calls.create")),
) -> CallOut:
    call = FundingCall(
        organization_id=principal.organization_id, created_by=principal.id, **payload.model_dump()
    )
    db.add(call)
    db.flush()
    audit.record(
        db,
        action="call.create",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="call",
        entity_id=call.id,
    )
    return CallOut.model_validate(call)


@router.get("/funding-calls/{call_id}", response_model=CallOut)
def get_call(
    call_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("calls.read")),
) -> CallOut:
    return CallOut.model_validate(get_org_scoped(db, FundingCall, call_id, principal))


@router.patch("/funding-calls/{call_id}", response_model=CallOut)
def update_call(
    call_id: uuid.UUID,
    payload: CallUpdate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("calls.update")),
) -> CallOut:
    call = get_org_scoped(db, FundingCall, call_id, principal)
    # Eligibility/deadline cannot be silently changed once published; require a new version.
    if call.status in {CallStatus.PUBLISHED, CallStatus.OPEN} and (
        payload.close_at is not None or payload.open_at is not None
    ):
        raise InvalidStateTransition(
            "Call đã công bố — thay đổi cửa sổ nộp phải tạo amendment/version."
        )
    apply_updates(call, payload.model_dump(exclude_unset=True))
    audit.record(
        db,
        action="call.update",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="call",
        entity_id=call.id,
    )
    return CallOut.model_validate(call)


@router.post("/funding-calls/{call_id}/publish", response_model=CallOut)
def publish_call(
    call_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("calls.update")),
) -> CallOut:
    call = get_org_scoped(db, FundingCall, call_id, principal)
    if call.status == CallStatus.ARCHIVED:
        raise InvalidStateTransition("Call đã lưu trữ.")
    call.status = CallStatus.PUBLISHED
    call.published_version += 1
    call.published_at = datetime.now(tz=UTC)
    audit.record(
        db,
        action="call.publish",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="call",
        entity_id=call.id,
        metadata={"version": call.published_version},
    )
    return CallOut.model_validate(call)


@router.post("/funding-calls/{call_id}/eligibility-rules", status_code=201)
def add_eligibility_rule(
    call_id: uuid.UUID,
    payload: EligibilityRuleIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("calls.update")),
) -> dict:
    call = get_org_scoped(db, FundingCall, call_id, principal)
    rule = EligibilityRule(
        organization_id=principal.organization_id, call_id=call.id, **payload.model_dump()
    )
    db.add(rule)
    return {"ok": True}
