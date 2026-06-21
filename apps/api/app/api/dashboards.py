"""Dashboards & reporting aggregates (traceable metrics)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import Principal, require
from app.models.outputs import ResearchOutput
from app.models.projects import FinanceTransaction, Project
from app.models.proposals import Proposal
from app.models.researchers import ResearcherProfile
from app.models.reviews import ReviewAssignment

router = APIRouter()


def _count(db: Session, model, *conds) -> int:
    stmt = select(func.count()).select_from(model)
    for c in conds:
        stmt = stmt.where(c)
    return int(db.scalar(stmt) or 0)


def _group_count(db: Session, model, col, org_id) -> dict[str, int]:
    rows = db.execute(
        select(col, func.count()).where(model.organization_id == org_id).group_by(col)
    ).all()
    return {str(k): int(v) for k, v in rows}


@router.get("/executive")
def executive(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("dashboards.read")),
) -> dict:
    org = principal.organization_id
    total_budget = db.scalar(
        select(func.coalesce(func.sum(Project.approved_budget), 0)).where(
            Project.organization_id == org
        )
    )
    disbursed = db.scalar(
        select(func.coalesce(func.sum(FinanceTransaction.amount), 0)).where(
            FinanceTransaction.organization_id == org,
            FinanceTransaction.transaction_type.in_(["DISBURSED", "ACTUAL"]),
        )
    )
    return {
        "metrics": {
            "researchers": _count(db, ResearcherProfile, ResearcherProfile.organization_id == org),
            "proposals": _count(db, Proposal, Proposal.organization_id == org),
            "projects_active": _count(
                db, Project, Project.organization_id == org, Project.status == "ACTIVE"
            ),
            "projects_total": _count(db, Project, Project.organization_id == org),
            "outputs": _count(db, ResearchOutput, ResearchOutput.organization_id == org),
            "outputs_verified": _count(
                db,
                ResearchOutput,
                ResearchOutput.organization_id == org,
                ResearchOutput.verification_status == "VERIFIED",
            ),
            "total_budget": float(total_budget or 0),
            "disbursed": float(disbursed or 0),
        },
        "proposals_by_status": _group_count(db, Proposal, Proposal.status, org),
        "projects_by_status": _group_count(db, Project, Project.status, org),
        "outputs_by_type": _group_count(db, ResearchOutput, ResearchOutput.output_type, org),
        "outputs_by_year": _group_count(db, ResearchOutput, ResearchOutput.year, org),
        "generated_at": datetime.now(UTC).isoformat(),
        "note": "Mỗi chỉ số có thể drill-down về bản ghi gốc trong phạm vi quyền.",
    }


@router.get("/research-office")
def research_office(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("dashboards.read")),
) -> dict:
    org = principal.organization_id
    return {
        "queues": {
            "proposals_submitted": _count(
                db, Proposal, Proposal.organization_id == org, Proposal.status == "SUBMITTED"
            ),
            "proposals_under_review": _count(
                db, Proposal, Proposal.organization_id == org, Proposal.status == "UNDER_REVIEW"
            ),
            "outputs_unverified": _count(
                db,
                ResearchOutput,
                ResearchOutput.organization_id == org,
                ResearchOutput.verification_status == "UNVERIFIED",
            ),
            "review_assignments_open": _count(
                db,
                ReviewAssignment,
                ReviewAssignment.organization_id == org,
                ReviewAssignment.status.in_(["INVITED", "ACCEPTED"]),
            ),
        },
        "data_quality": {
            "outputs_missing_doi": _count(
                db,
                ResearchOutput,
                ResearchOutput.organization_id == org,
                ResearchOutput.doi.is_(None),
                ResearchOutput.output_type == "JOURNAL_ARTICLE",
            ),
        },
    }


@router.get("/researcher")
def researcher(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("dashboards.read")),
) -> dict:
    org = principal.organization_id
    return {
        "my_proposals": _count(
            db, Proposal, Proposal.organization_id == org, Proposal.pi_id == principal.id
        ),
        "my_projects": _count(
            db, Project, Project.organization_id == org, Project.pi_id == principal.id
        ),
    }
