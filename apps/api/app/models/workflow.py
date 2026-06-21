"""Generic workflow, tasks, approvals and notifications."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import BaseModel
from app.core.enums import ApprovalDecision, NotificationStatus, WorkflowTaskStatus


class WorkflowTemplate(BaseModel):
    __tablename__ = "workflow_templates"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(255))
    entity_type: Mapped[str] = mapped_column(String(40))
    version_no: Mapped[int] = mapped_column(Integer, default=1)
    definition_json: Mapped[dict] = mapped_column(JSONB, default=dict)  # states/transitions/guards
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class WorkflowInstance(BaseModel):
    __tablename__ = "workflow_instances"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    template_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(40), index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    current_state: Mapped[str | None] = mapped_column(String(40), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkflowTask(BaseModel):
    """A task in someone's inbox (assigned to user/role/unit)."""

    __tablename__ = "workflow_tasks"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    entity_type: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, index=True
    )
    assignee_type: Mapped[str] = mapped_column(String(20), default="USER")  # USER|ROLE|UNIT
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, index=True
    )
    task_type: Mapped[str] = mapped_column(String(40), default="ACTION")
    priority: Mapped[str] = mapped_column(String(10), default="NORMAL")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=WorkflowTaskStatus.OPEN, index=True)
    outcome: Mapped[str | None] = mapped_column(String(40), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Approval(BaseModel):
    __tablename__ = "approvals"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    entity_type: Mapped[str] = mapped_column(String(40), index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    step_name: Mapped[str] = mapped_column(String(80))
    approval_type: Mapped[str] = mapped_column(String(20), default="SEQUENTIAL")
    approver_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    decision: Mapped[str] = mapped_column(String(20), default=ApprovalDecision.PENDING)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Comment(BaseModel):
    __tablename__ = "comments"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    entity_type: Mapped[str] = mapped_column(String(40), index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    author_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    author_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body: Mapped[str] = mapped_column(Text)
    mentions: Mapped[list] = mapped_column(JSONB, default=list)


class Notification(BaseModel):
    __tablename__ = "notifications"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(40), default="GENERAL")
    entity_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=NotificationStatus.UNREAD, index=True)
    sent_email: Mapped[bool] = mapped_column(Boolean, default=False)
