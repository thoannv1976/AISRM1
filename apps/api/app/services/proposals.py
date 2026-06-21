"""Proposal domain service: validation, submission, decision, activation."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import Principal
from app.core.enums import (
    DecisionOutcome,
    DocumentStatus,
    ProjectStatus,
    ProposalStatus,
)
from app.core.errors import (
    DeadlinePassed,
    DocumentQuarantined,
    InvalidStateTransition,
    SubmissionIncomplete,
)
from app.models.documents import Document
from app.models.funding import FundingCall
from app.models.projects import Project, ProjectBaseline
from app.models.proposals import (
    Deliverable,
    Milestone,
    Proposal,
    ProposalBudgetLine,
    ProposalTeamMember,
    ProposalVersion,
    Submission,
    WorkPackage,
)
from app.models.reviews import Decision
from app.services import audit
from app.services.numbering import next_code


def validate_proposal(db: Session, proposal: Proposal) -> list[dict]:
    """Return a list of validation issues (DQ-06)."""
    issues: list[dict] = []

    def err(code, msg, field=None, severity="ERROR"):
        issues.append({"code": code, "severity": severity, "message": msg, "field": field})

    if not proposal.title:
        err("MISSING_TITLE", "Thiếu tên đề tài.", "title")
    if not proposal.pi_id:
        err("MISSING_PI", "Thiếu chủ nhiệm đề tài.", "pi_id")
    if not proposal.lead_unit_id:
        err("MISSING_LEAD_UNIT", "Thiếu đơn vị chủ trì.", "lead_unit_id")
    content = proposal.content_json or {}
    if not content.get("objectives"):
        err("MISSING_OBJECTIVES", "Thiếu mục tiêu nghiên cứu.", "content_json.objectives")
    if not content.get("methods"):
        err("MISSING_METHODS", "Thiếu phương pháp nghiên cứu.", "content_json.methods")

    team = db.scalars(
        select(ProposalTeamMember).where(ProposalTeamMember.proposal_id == proposal.id)
    ).all()
    if not team:
        err("MISSING_TEAM", "Thiếu thành viên nhóm nghiên cứu.", "team")

    deliverables = db.scalars(
        select(Deliverable).where(Deliverable.proposal_id == proposal.id)
    ).all()
    if not deliverables:
        err("MISSING_DELIVERABLES", "Thiếu sản phẩm cam kết.", "deliverables")

    budget = db.scalars(
        select(ProposalBudgetLine).where(ProposalBudgetLine.proposal_id == proposal.id)
    ).all()
    if not budget:
        err("MISSING_BUDGET", "Thiếu dự toán kinh phí.", "budget")

    # Required documents from the call
    call = db.get(FundingCall, proposal.call_id)
    if call and call.required_documents:
        linked = db.scalars(
            select(Document).where(
                Document.entity_type == "proposal", Document.entity_id == proposal.id
            )
        ).all()
        link_roles = {d.link_role for d in linked}
        for req in call.required_documents:
            if req not in link_roles:
                err(
                    "MISSING_DOCUMENT",
                    f"Thiếu tài liệu bắt buộc: {req}.",
                    f"documents.{req}",
                    "WARNING",
                )

    # Quarantined files block submission
    quarantined = db.scalar(
        select(Document).where(
            Document.entity_type == "proposal",
            Document.entity_id == proposal.id,
            Document.status == DocumentStatus.QUARANTINED,
        )
    )
    if quarantined:
        err("FILE_QUARANTINED", "Có tệp chưa qua kiểm tra an toàn.", "documents")

    return issues


def _snapshot(proposal: Proposal, team, wps, deliverables, budget) -> dict:
    return {
        "title": proposal.title,
        "abstract": proposal.abstract,
        "content": proposal.content_json,
        "budget_total": str(proposal.budget_total),
        "team": [
            {
                "researcher_id": str(t.researcher_id) if t.researcher_id else None,
                "name": t.external_person_name,
                "role": t.role,
            }
            for t in team
        ],
        "work_packages": [{"code": w.code, "title": w.title} for w in wps],
        "deliverables": [{"code": d.code, "title": d.title} for d in deliverables],
        "budget_lines": [{"category": b.category, "amount": str(b.amount)} for b in budget],
    }


def submit_proposal(
    db: Session, principal: Principal, proposal: Proposal, note: str | None
) -> Submission:
    if proposal.status not in {ProposalStatus.DRAFT, ProposalStatus.INTERNAL_REVIEW}:
        raise InvalidStateTransition("Chỉ nộp được hồ sơ ở trạng thái nháp/đang duyệt nội bộ.")

    issues = validate_proposal(db, proposal)
    errors = [i for i in issues if i["severity"] == "ERROR"]
    if errors:
        raise SubmissionIncomplete(
            "Hồ sơ chưa đầy đủ để nộp.",
            field_errors={i["field"] or i["code"]: i["message"] for i in errors},
        )

    if any(i["code"] == "FILE_QUARANTINED" for i in issues):
        raise DocumentQuarantined()

    call = db.get(FundingCall, proposal.call_id)
    now = datetime.now(tz=UTC)
    if call and call.close_at and now > call.close_at:
        raise DeadlinePassed("Đã quá hạn nộp hồ sơ của call.")

    team = db.scalars(
        select(ProposalTeamMember).where(ProposalTeamMember.proposal_id == proposal.id)
    ).all()
    wps = db.scalars(select(WorkPackage).where(WorkPackage.proposal_id == proposal.id)).all()
    deliverables = db.scalars(
        select(Deliverable).where(Deliverable.proposal_id == proposal.id)
    ).all()
    budget = db.scalars(
        select(ProposalBudgetLine).where(ProposalBudgetLine.proposal_id == proposal.id)
    ).all()

    snapshot = _snapshot(proposal, team, wps, deliverables, budget)
    snapshot_hash = (
        "sha256:"
        + hashlib.sha256(
            json.dumps(snapshot, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
    )

    last_version = db.scalar(
        select(ProposalVersion)
        .where(ProposalVersion.proposal_id == proposal.id)
        .order_by(ProposalVersion.version_no.desc())
    )
    next_no = (last_version.version_no + 1) if last_version else 1
    version = ProposalVersion(
        organization_id=proposal.organization_id,
        proposal_id=proposal.id,
        version_no=next_no,
        content_json=snapshot,
        budget_total=proposal.budget_total,
        submitted_at=now,
        snapshot_hash=snapshot_hash,
        is_immutable=True,
    )
    db.add(version)
    db.flush()

    submission = Submission(
        organization_id=proposal.organization_id,
        proposal_id=proposal.id,
        version_id=version.id,
        submitted_at=now,
        submitted_by=principal.id,
        snapshot_hash=snapshot_hash,
        note=note,
        receipt_no=next_code(db, Submission, "RCPT", proposal.organization_id),
    )
    db.add(submission)
    proposal.status = ProposalStatus.SUBMITTED
    proposal.submitted_at = now
    proposal.current_version_id = version.id
    proposal.version += 1

    audit.record(
        db,
        action="proposal.submit",
        actor_id=principal.id,
        organization_id=proposal.organization_id,
        entity_type="proposal",
        entity_id=proposal.id,
        metadata={"snapshot_hash": snapshot_hash},
    )
    return submission


def make_decision(
    db: Session,
    principal: Principal,
    proposal: Proposal,
    *,
    outcome: str,
    decision_no: str | None,
    conditions: str | None,
    approved_budget,
) -> Decision:
    if proposal.status not in {
        ProposalStatus.SUBMITTED,
        ProposalStatus.UNDER_REVIEW,
        ProposalStatus.COUNCIL,
        ProposalStatus.ELIGIBLE,
        ProposalStatus.ADMIN_CHECK,
    }:
        raise InvalidStateTransition("Hồ sơ không ở trạng thái có thể ra quyết định.")

    decision = Decision(
        organization_id=proposal.organization_id,
        scope_type="proposal",
        scope_id=proposal.id,
        decision_type="FUNDING",
        decision_no=decision_no,
        decision_date=datetime.now(tz=UTC),
        outcome=outcome,
        conditions=conditions,
        approved_budget=approved_budget,
        approved_by=principal.id,
    )
    db.add(decision)
    if outcome in {DecisionOutcome.APPROVED, DecisionOutcome.APPROVED_WITH_CONDITIONS}:
        proposal.status = ProposalStatus.APPROVED
    elif outcome == DecisionOutcome.REJECTED:
        proposal.status = ProposalStatus.REJECTED
    proposal.version += 1
    audit.record(
        db,
        action="proposal.decision",
        actor_id=principal.id,
        organization_id=proposal.organization_id,
        entity_type="proposal",
        entity_id=proposal.id,
        metadata={"outcome": outcome},
    )
    db.flush()
    return decision


def activate_project(db: Session, principal: Principal, proposal: Proposal) -> Project:
    if proposal.status != ProposalStatus.APPROVED:
        raise InvalidStateTransition("Chỉ kích hoạt đề tài từ hồ sơ đã được duyệt.")
    existing = db.scalar(select(Project).where(Project.proposal_id == proposal.id))
    if existing:
        raise InvalidStateTransition("Đề tài đã được kích hoạt từ hồ sơ này.")

    decision = db.scalar(
        select(Decision)
        .where(Decision.scope_type == "proposal", Decision.scope_id == proposal.id)
        .order_by(Decision.created_at.desc())
    )
    approved_budget = (
        decision.approved_budget if decision and decision.approved_budget else proposal.budget_total
    )

    project = Project(
        organization_id=proposal.organization_id,
        proposal_id=proposal.id,
        project_code=next_code(db, Project, "DT", proposal.organization_id),
        title=proposal.title,
        pi_id=proposal.pi_id,
        lead_unit_id=proposal.lead_unit_id,
        status=ProjectStatus.ACTIVE,
        start_date=proposal.start_date,
        approved_budget=approved_budget,
        currency=proposal.currency,
        decision_id=decision.id if decision else None,
        created_by=principal.id,
    )
    db.add(project)
    db.flush()

    # Copy plan items to the project as the baseline plan.
    for wp in db.scalars(select(WorkPackage).where(WorkPackage.proposal_id == proposal.id)).all():
        db.add(
            WorkPackage(
                organization_id=project.organization_id,
                project_id=project.id,
                code=wp.code,
                title=wp.title,
                objectives=wp.objectives,
                start_month=wp.start_month,
                end_month=wp.end_month,
                order_no=wp.order_no,
            )
        )
    for ms in db.scalars(select(Milestone).where(Milestone.proposal_id == proposal.id)).all():
        db.add(
            Milestone(
                organization_id=project.organization_id,
                project_id=project.id,
                code=ms.code,
                title=ms.title,
                due_date=ms.due_date,
                order_no=ms.order_no,
            )
        )
    for d in db.scalars(select(Deliverable).where(Deliverable.proposal_id == proposal.id)).all():
        db.add(
            Deliverable(
                organization_id=project.organization_id,
                project_id=project.id,
                code=d.code,
                title=d.title,
                deliverable_type=d.deliverable_type,
                due_date=d.due_date,
                acceptance_criteria=d.acceptance_criteria,
                target_value=d.target_value,
            )
        )

    db.add(
        ProjectBaseline(
            organization_id=project.organization_id,
            project_id=project.id,
            baseline_no=1,
            scope_json={"from_proposal": str(proposal.id)},
            budget_total=approved_budget,
            effective_at=datetime.now(tz=UTC),
            approved_decision_id=decision.id if decision else None,
        )
    )
    audit.record(
        db,
        action="project.activate",
        actor_id=principal.id,
        organization_id=project.organization_id,
        entity_type="project",
        entity_id=project.id,
        metadata={"proposal_id": str(proposal.id)},
    )
    db.flush()
    return project
