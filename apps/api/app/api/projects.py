"""Project lifecycle endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api._helpers import apply_updates, check_version, get_org_scoped
from app.core.db import get_db
from app.core.deps import Principal, require
from app.core.enums import ProjectStatus, ReportStatus
from app.core.errors import InvalidStateTransition
from app.core.pagination import Page, PageParams, build_page, page_params, paginate
from app.models.projects import (
    ChangeRequest,
    Closure,
    FinanceTransaction,
    ProgressReport,
    Project,
    ProjectTask,
    Risk,
)
from app.schemas.projects import (
    ChangeRequestIn,
    ClosureIn,
    FinanceTxnIn,
    ProgressReportIn,
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
    RiskIn,
    TaskIn,
    TaskOut,
    TransitionIn,
)
from app.services import audit
from app.services.numbering import next_code

router = APIRouter()

# Allowed project status transitions (state machine)
TRANSITIONS: dict[str, set[str]] = {
    ProjectStatus.PENDING_ACTIVATION: {ProjectStatus.ACTIVE, ProjectStatus.TERMINATED},
    ProjectStatus.ACTIVE: {
        ProjectStatus.SUSPENDED,
        ProjectStatus.CHANGE_PENDING,
        ProjectStatus.CLOSING,
        ProjectStatus.TERMINATED,
    },
    ProjectStatus.SUSPENDED: {ProjectStatus.ACTIVE, ProjectStatus.TERMINATED},
    ProjectStatus.CHANGE_PENDING: {ProjectStatus.ACTIVE, ProjectStatus.TERMINATED},
    ProjectStatus.CLOSING: {ProjectStatus.UNDER_ACCEPTANCE, ProjectStatus.ACTIVE},
    ProjectStatus.UNDER_ACCEPTANCE: {ProjectStatus.COMPLETED, ProjectStatus.CLOSING},
}


@router.get("", response_model=Page[ProjectOut])
def list_projects(
    status: str | None = None,
    mine: bool = False,
    db: Session = Depends(get_db),
    params: PageParams = Depends(page_params),
    principal: Principal = Depends(require("projects.read")),
) -> Page[ProjectOut]:
    stmt = select(Project).where(Project.organization_id == principal.organization_id)
    if status:
        stmt = stmt.where(Project.status == status)
    if mine:
        stmt = stmt.where(Project.pi_id == principal.id)
    stmt = stmt.order_by(Project.created_at.desc())
    items, total = paginate(db, stmt, params)
    return build_page([ProjectOut.model_validate(i) for i in items], total, params)


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("projects.create")),
) -> ProjectOut:
    project = Project(
        organization_id=principal.organization_id,
        project_code=payload.project_code
        or next_code(db, Project, "DT", principal.organization_id),
        title=payload.title,
        pi_id=payload.pi_id,
        lead_unit_id=payload.lead_unit_id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        approved_budget=payload.approved_budget,
        currency=payload.currency,
        contract_no=payload.contract_no,
        status=ProjectStatus.ACTIVE,
        created_by=principal.id,
    )
    db.add(project)
    db.flush()
    audit.record(
        db,
        action="project.create",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="project",
        entity_id=project.id,
    )
    return ProjectOut.model_validate(project)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("projects.read")),
) -> ProjectOut:
    return ProjectOut.model_validate(get_org_scoped(db, Project, project_id, principal))


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("projects.update")),
) -> ProjectOut:
    project = get_org_scoped(db, Project, project_id, principal)
    check_version(project, payload.version)
    apply_updates(project, payload.model_dump(exclude_unset=True))
    audit.record(
        db,
        action="project.update",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="project",
        entity_id=project.id,
    )
    return ProjectOut.model_validate(project)


@router.post("/{project_id}/transition", response_model=ProjectOut)
def transition(
    project_id: uuid.UUID,
    payload: TransitionIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("projects.update")),
) -> ProjectOut:
    project = get_org_scoped(db, Project, project_id, principal)
    allowed = TRANSITIONS.get(project.status, set())
    if payload.target_status not in allowed:
        raise InvalidStateTransition(
            f"Không thể chuyển {project.status} → {payload.target_status}."
        )
    project.status = payload.target_status
    project.version += 1
    audit.record(
        db,
        action="project.transition",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="project",
        entity_id=project.id,
        metadata={"to": payload.target_status, "reason": payload.reason},
    )
    return ProjectOut.model_validate(project)


# ----- Tasks -----
@router.get("/{project_id}/tasks", response_model=list[TaskOut])
def list_tasks(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("projects.read")),
) -> list[TaskOut]:
    get_org_scoped(db, Project, project_id, principal)
    rows = db.scalars(
        select(ProjectTask)
        .where(ProjectTask.project_id == project_id)
        .order_by(ProjectTask.order_no)
    ).all()
    return [TaskOut.model_validate(t) for t in rows]


@router.post("/{project_id}/tasks", response_model=TaskOut, status_code=201)
def add_task(
    project_id: uuid.UUID,
    payload: TaskIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("projects.update")),
) -> TaskOut:
    get_org_scoped(db, Project, project_id, principal)
    task = ProjectTask(
        organization_id=principal.organization_id, project_id=project_id, **payload.model_dump()
    )
    db.add(task)
    db.flush()
    return TaskOut.model_validate(task)


# ----- Progress reports -----
@router.post("/{project_id}/progress-reports", status_code=201)
def add_progress_report(
    project_id: uuid.UUID,
    payload: ProgressReportIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("projects.update")),
) -> dict:
    project = get_org_scoped(db, Project, project_id, principal)
    report = ProgressReport(
        organization_id=principal.organization_id,
        project_id=project.id,
        status=ReportStatus.SUBMITTED,
        submitted_at=datetime.now(tz=UTC),
        **payload.model_dump(),
    )
    db.add(report)
    if payload.completion_percent:
        project.completion_percent = payload.completion_percent
    audit.record(
        db,
        action="project.progress_report",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="project",
        entity_id=project.id,
    )
    db.flush()
    return {"ok": True, "report_id": str(report.id)}


# ----- Change requests -----
@router.post("/{project_id}/change-requests", status_code=201)
def add_change_request(
    project_id: uuid.UUID,
    payload: ChangeRequestIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("projects.update")),
) -> dict:
    project = get_org_scoped(db, Project, project_id, principal)
    cr = ChangeRequest(
        organization_id=principal.organization_id,
        project_id=project.id,
        status="SUBMITTED",
        **payload.model_dump(),
    )
    db.add(cr)
    db.flush()
    return {"ok": True, "change_request_id": str(cr.id)}


# ----- Risks -----
@router.post("/{project_id}/risks", status_code=201)
def add_risk(
    project_id: uuid.UUID,
    payload: RiskIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("projects.update")),
) -> dict:
    get_org_scoped(db, Project, project_id, principal)
    data = payload.model_dump()
    risk = Risk(
        organization_id=principal.organization_id,
        project_id=project_id,
        score=data["probability"] * data["impact"],
        **data,
    )
    db.add(risk)
    return {"ok": True}


# ----- Finance (administrative view) -----
@router.post("/{project_id}/finance-transactions", status_code=201)
def add_finance_txn(
    project_id: uuid.UUID,
    payload: FinanceTxnIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("finance.read", "projects.update")),
) -> dict:
    get_org_scoped(db, Project, project_id, principal)
    txn = FinanceTransaction(
        organization_id=principal.organization_id,
        project_id=project_id,
        synced_at=datetime.now(tz=UTC),
        **payload.model_dump(),
    )
    db.add(txn)
    return {"ok": True}


@router.get("/{project_id}/finance-summary")
def finance_summary(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("finance.read")),
) -> dict:
    project = get_org_scoped(db, Project, project_id, principal)
    txns = db.scalars(
        select(FinanceTransaction).where(FinanceTransaction.project_id == project_id)
    ).all()
    by_type: dict[str, float] = {}
    for t in txns:
        by_type[t.transaction_type] = by_type.get(t.transaction_type, 0.0) + float(t.amount)
    disbursed = by_type.get("DISBURSED", 0.0) + by_type.get("ACTUAL", 0.0)
    budget = float(project.approved_budget or 0)
    return {
        "approved_budget": budget,
        "by_type": by_type,
        "disbursed": disbursed,
        "variance": budget - disbursed,
        "burn_rate": round(disbursed / budget, 3) if budget else None,
        "source_note": "Số liệu mang tính quản trị; ERP là nguồn chuẩn.",
    }


# ----- Closure -----
@router.post("/{project_id}/closure", status_code=201)
def close_project(
    project_id: uuid.UUID,
    payload: ClosureIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("projects.update")),
) -> dict:
    project = get_org_scoped(db, Project, project_id, principal)
    if project.status not in {ProjectStatus.UNDER_ACCEPTANCE, ProjectStatus.CLOSING}:
        raise InvalidStateTransition("Đề tài phải ở trạng thái closing/under_acceptance.")
    closure = Closure(
        organization_id=principal.organization_id,
        project_id=project.id,
        closed_at=datetime.now(tz=UTC),
        **payload.model_dump(),
    )
    db.add(closure)
    project.status = ProjectStatus.COMPLETED
    project.grade = payload.result
    project.version += 1
    audit.record(
        db,
        action="project.closure",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="project",
        entity_id=project.id,
    )
    return {"ok": True}
