"""Task inbox, notifications, comments and audit log endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api._helpers import get_org_scoped
from app.core.db import get_db
from app.core.deps import Principal, get_principal, require
from app.core.enums import NotificationStatus, WorkflowTaskStatus
from app.core.pagination import Page, PageParams, build_page, page_params, paginate
from app.models.identity import AuditLog
from app.models.workflow import Comment, Notification, WorkflowTask
from app.schemas.workflow import (
    AuditOut,
    CommentIn,
    CommentOut,
    NotificationOut,
    TaskCompleteIn,
    TaskOut,
)
from app.services import audit

router = APIRouter()


@router.get("/tasks/inbox", response_model=Page[TaskOut])
def task_inbox(
    status: str | None = None,
    db: Session = Depends(get_db),
    params: PageParams = Depends(page_params),
    principal: Principal = Depends(get_principal),
) -> Page[TaskOut]:
    stmt = select(WorkflowTask).where(
        WorkflowTask.organization_id == principal.organization_id,
        or_(
            WorkflowTask.assignee_id == principal.id,
            WorkflowTask.assignee_id.in_(list(principal.unit_scopes))
            if principal.unit_scopes
            else False,
        ),
    )
    if status:
        stmt = stmt.where(WorkflowTask.status == status)
    else:
        stmt = stmt.where(WorkflowTask.status != WorkflowTaskStatus.COMPLETED)
    stmt = stmt.order_by(WorkflowTask.due_at.asc().nullslast())
    items, total = paginate(db, stmt, params)
    return build_page([TaskOut.model_validate(i) for i in items], total, params)


@router.post("/tasks/{task_id}/complete", response_model=TaskOut)
def complete_task(
    task_id: uuid.UUID,
    payload: TaskCompleteIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_principal),
) -> TaskOut:
    task = get_org_scoped(db, WorkflowTask, task_id, principal)
    task.status = WorkflowTaskStatus.COMPLETED
    task.outcome = payload.outcome
    task.completed_at = datetime.now(tz=UTC)
    audit.record(
        db,
        action="task.complete",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="task",
        entity_id=task.id,
    )
    return TaskOut.model_validate(task)


@router.get("/notifications", response_model=Page[NotificationOut])
def list_notifications(
    db: Session = Depends(get_db),
    params: PageParams = Depends(page_params),
    principal: Principal = Depends(get_principal),
) -> Page[NotificationOut]:
    stmt = (
        select(Notification)
        .where(
            Notification.organization_id == principal.organization_id,
            Notification.user_id == principal.id,
        )
        .order_by(Notification.created_at.desc())
    )
    items, total = paginate(db, stmt, params)
    return build_page([NotificationOut.model_validate(i) for i in items], total, params)


@router.post("/notifications/{notification_id}/read", response_model=NotificationOut)
def mark_read(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_principal),
) -> NotificationOut:
    n = get_org_scoped(db, Notification, notification_id, principal)
    n.status = NotificationStatus.READ
    return NotificationOut.model_validate(n)


@router.get("/comments", response_model=list[CommentOut])
def list_comments(
    entity_type: str,
    entity_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_principal),
) -> list[CommentOut]:
    rows = db.scalars(
        select(Comment)
        .where(
            Comment.organization_id == principal.organization_id,
            Comment.entity_type == entity_type,
            Comment.entity_id == entity_id,
        )
        .order_by(Comment.created_at)
    ).all()
    return [CommentOut.model_validate(c) for c in rows]


@router.post("/comments", response_model=CommentOut, status_code=201)
def add_comment(
    payload: CommentIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_principal),
) -> CommentOut:
    c = Comment(
        organization_id=principal.organization_id,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        author_id=principal.id,
        author_name=principal.user.display_name,
        body=payload.body,
        mentions=payload.mentions,
    )
    db.add(c)
    db.flush()
    return CommentOut.model_validate(c)


@router.get("/audit-logs", response_model=Page[AuditOut])
def list_audit(
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    action: str | None = None,
    db: Session = Depends(get_db),
    params: PageParams = Depends(page_params),
    principal: Principal = Depends(require("audit.read")),
) -> Page[AuditOut]:
    stmt = select(AuditLog).where(AuditLog.organization_id == principal.organization_id)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    stmt = stmt.order_by(AuditLog.occurred_at.desc())
    items, total = paginate(db, stmt, params)
    return build_page([AuditOut.model_validate(i) for i in items], total, params)
