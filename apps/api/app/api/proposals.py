"""Proposal workspace endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api._helpers import apply_updates, check_version, get_org_scoped
from app.core.db import get_db
from app.core.deps import Principal, require
from app.core.enums import ProposalStatus
from app.core.errors import InvalidStateTransition
from app.core.pagination import Page, PageParams, build_page, page_params, paginate
from app.models.proposals import (
    Deliverable,
    Milestone,
    Proposal,
    ProposalBudgetLine,
    ProposalTeamMember,
    WorkPackage,
)
from app.schemas.proposals import (
    BudgetLineIn,
    DecisionIn,
    DeliverableIn,
    MilestoneIn,
    ProposalCreate,
    ProposalOut,
    ProposalUpdate,
    SubmitIn,
    TeamMemberIn,
    ValidationOut,
    WorkPackageIn,
)
from app.services import audit
from app.services.numbering import next_code
from app.services.proposals import (
    activate_project,
    make_decision,
    submit_proposal,
    validate_proposal,
)

router = APIRouter()


def _recompute_budget(db: Session, proposal: Proposal) -> None:
    lines = db.scalars(
        select(ProposalBudgetLine).where(ProposalBudgetLine.proposal_id == proposal.id)
    ).all()
    proposal.budget_total = sum((line.amount for line in lines), start=0)


@router.get("", response_model=Page[ProposalOut])
def list_proposals(
    call_id: uuid.UUID | None = None,
    status: str | None = None,
    mine: bool = False,
    db: Session = Depends(get_db),
    params: PageParams = Depends(page_params),
    principal: Principal = Depends(require("proposals.read")),
) -> Page[ProposalOut]:
    stmt = select(Proposal).where(Proposal.organization_id == principal.organization_id)
    if call_id:
        stmt = stmt.where(Proposal.call_id == call_id)
    if status:
        stmt = stmt.where(Proposal.status == status)
    if mine:
        stmt = stmt.where(Proposal.pi_id == principal.id)
    stmt = stmt.order_by(Proposal.created_at.desc())
    items, total = paginate(db, stmt, params)
    return build_page([ProposalOut.model_validate(i) for i in items], total, params)


@router.post("", response_model=ProposalOut, status_code=201)
def create_proposal(
    payload: ProposalCreate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("proposals.create")),
) -> ProposalOut:
    proposal = Proposal(
        organization_id=principal.organization_id,
        call_id=payload.call_id,
        proposal_code=next_code(db, Proposal, "PROP", principal.organization_id),
        title=payload.title,
        title_en=payload.title_en,
        abstract=payload.abstract,
        pi_id=payload.pi_id or principal.id,
        lead_unit_id=payload.lead_unit_id or principal.user.primary_unit_id,
        duration_months=payload.duration_months,
        fields=payload.fields,
        sdgs=payload.sdgs,
        keywords=payload.keywords,
        status=ProposalStatus.DRAFT,
        created_by=principal.id,
    )
    db.add(proposal)
    db.flush()
    audit.record(
        db,
        action="proposal.create",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="proposal",
        entity_id=proposal.id,
    )
    return ProposalOut.model_validate(proposal)


@router.get("/{proposal_id}", response_model=ProposalOut)
def get_proposal(
    proposal_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("proposals.read")),
) -> ProposalOut:
    return ProposalOut.model_validate(get_org_scoped(db, Proposal, proposal_id, principal))


@router.patch("/{proposal_id}", response_model=ProposalOut)
def update_proposal(
    proposal_id: uuid.UUID,
    payload: ProposalUpdate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("proposals.update")),
) -> ProposalOut:
    proposal = get_org_scoped(db, Proposal, proposal_id, principal)
    if proposal.status not in {ProposalStatus.DRAFT, ProposalStatus.INTERNAL_REVIEW}:
        raise InvalidStateTransition("Hồ sơ đã nộp — không thể sửa nội dung chính.")
    check_version(proposal, payload.version)
    apply_updates(proposal, payload.model_dump(exclude_unset=True))
    audit.record(
        db,
        action="proposal.update",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="proposal",
        entity_id=proposal.id,
    )
    return ProposalOut.model_validate(proposal)


# ----- Sub-resources -----
@router.post("/{proposal_id}/team", status_code=201)
def add_team_member(
    proposal_id: uuid.UUID,
    payload: TeamMemberIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("proposals.update")),
) -> dict:
    proposal = get_org_scoped(db, Proposal, proposal_id, principal)
    db.add(
        ProposalTeamMember(
            organization_id=principal.organization_id,
            proposal_id=proposal.id,
            **payload.model_dump(),
        )
    )
    return {"ok": True}


@router.post("/{proposal_id}/work-packages", status_code=201)
def add_work_package(
    proposal_id: uuid.UUID,
    payload: WorkPackageIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("proposals.update")),
) -> dict:
    proposal = get_org_scoped(db, Proposal, proposal_id, principal)
    db.add(
        WorkPackage(
            organization_id=principal.organization_id,
            proposal_id=proposal.id,
            **payload.model_dump(),
        )
    )
    return {"ok": True}


@router.post("/{proposal_id}/milestones", status_code=201)
def add_milestone(
    proposal_id: uuid.UUID,
    payload: MilestoneIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("proposals.update")),
) -> dict:
    proposal = get_org_scoped(db, Proposal, proposal_id, principal)
    db.add(
        Milestone(
            organization_id=principal.organization_id,
            proposal_id=proposal.id,
            **payload.model_dump(),
        )
    )
    return {"ok": True}


@router.post("/{proposal_id}/deliverables", status_code=201)
def add_deliverable(
    proposal_id: uuid.UUID,
    payload: DeliverableIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("proposals.update")),
) -> dict:
    proposal = get_org_scoped(db, Proposal, proposal_id, principal)
    db.add(
        Deliverable(
            organization_id=principal.organization_id,
            proposal_id=proposal.id,
            **payload.model_dump(),
        )
    )
    return {"ok": True}


@router.post("/{proposal_id}/budget-lines", status_code=201)
def add_budget_line(
    proposal_id: uuid.UUID,
    payload: BudgetLineIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("proposals.update")),
) -> dict:
    proposal = get_org_scoped(db, Proposal, proposal_id, principal)
    db.add(
        ProposalBudgetLine(
            organization_id=principal.organization_id,
            proposal_id=proposal.id,
            **payload.model_dump(),
        )
    )
    db.flush()
    _recompute_budget(db, proposal)
    return {"ok": True, "budget_total": str(proposal.budget_total)}


@router.get("/{proposal_id}/detail")
def proposal_detail(
    proposal_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("proposals.read")),
) -> dict:
    p = get_org_scoped(db, Proposal, proposal_id, principal)
    team = db.scalars(
        select(ProposalTeamMember).where(ProposalTeamMember.proposal_id == p.id)
    ).all()
    wps = db.scalars(select(WorkPackage).where(WorkPackage.proposal_id == p.id)).all()
    ms = db.scalars(select(Milestone).where(Milestone.proposal_id == p.id)).all()
    dels = db.scalars(select(Deliverable).where(Deliverable.proposal_id == p.id)).all()
    budget = db.scalars(
        select(ProposalBudgetLine).where(ProposalBudgetLine.proposal_id == p.id)
    ).all()
    return {
        "proposal": ProposalOut.model_validate(p).model_dump(mode="json"),
        "team": [
            {
                "id": str(t.id),
                "name": t.external_person_name,
                "role": t.role,
                "researcher_id": str(t.researcher_id) if t.researcher_id else None,
            }
            for t in team
        ],
        "work_packages": [{"id": str(w.id), "code": w.code, "title": w.title} for w in wps],
        "milestones": [
            {
                "id": str(m.id),
                "code": m.code,
                "title": m.title,
                "due_date": str(m.due_date) if m.due_date else None,
            }
            for m in ms
        ],
        "deliverables": [
            {"id": str(d.id), "code": d.code, "title": d.title, "type": d.deliverable_type}
            for d in dels
        ],
        "budget_lines": [
            {"id": str(b.id), "category": b.category, "amount": str(b.amount), "year": b.year}
            for b in budget
        ],
    }


@router.post("/{proposal_id}/validate", response_model=ValidationOut)
def validate(
    proposal_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("proposals.read")),
) -> ValidationOut:
    proposal = get_org_scoped(db, Proposal, proposal_id, principal)
    issues = validate_proposal(db, proposal)
    ok = not any(i["severity"] == "ERROR" for i in issues)
    return ValidationOut(ok=ok, issues=issues)


@router.post("/{proposal_id}/submit", response_model=ProposalOut)
def submit(
    proposal_id: uuid.UUID,
    payload: SubmitIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("proposals.submit")),
) -> ProposalOut:
    proposal = get_org_scoped(db, Proposal, proposal_id, principal)
    submit_proposal(db, principal, proposal, payload.submission_note)
    return ProposalOut.model_validate(proposal)


@router.post("/{proposal_id}/withdraw", response_model=ProposalOut)
def withdraw(
    proposal_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("proposals.update")),
) -> ProposalOut:
    proposal = get_org_scoped(db, Proposal, proposal_id, principal)
    if proposal.status in {ProposalStatus.APPROVED, ProposalStatus.REJECTED}:
        raise InvalidStateTransition("Không thể rút hồ sơ đã có quyết định.")
    proposal.status = ProposalStatus.WITHDRAWN
    proposal.version += 1
    audit.record(
        db,
        action="proposal.withdraw",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="proposal",
        entity_id=proposal.id,
    )
    return ProposalOut.model_validate(proposal)


@router.post("/{proposal_id}/decision")
def decision(
    proposal_id: uuid.UUID,
    payload: DecisionIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("decisions.create")),
) -> dict:
    proposal = get_org_scoped(db, Proposal, proposal_id, principal)
    d = make_decision(
        db,
        principal,
        proposal,
        outcome=payload.outcome,
        decision_no=payload.decision_no,
        conditions=payload.conditions,
        approved_budget=payload.approved_budget,
    )
    return {"ok": True, "decision_id": str(d.id), "proposal_status": proposal.status}


@router.post("/{proposal_id}/activate-project")
def activate(
    proposal_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("projects.create", "decisions.create")),
) -> dict:
    proposal = get_org_scoped(db, Proposal, proposal_id, principal)
    project = activate_project(db, principal, proposal)
    return {"ok": True, "project_id": str(project.id), "project_code": project.project_code}
