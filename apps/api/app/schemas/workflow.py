"""Workflow, task, notification schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import IdMixin


class TaskOut(IdMixin):
    organization_id: uuid.UUID
    title: str
    description: str | None = None
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    task_type: str
    priority: str
    due_at: datetime | None = None
    status: str


class TaskCompleteIn(BaseModel):
    outcome: str | None = None
    comment: str | None = None


class NotificationOut(IdMixin):
    title: str
    body: str | None = None
    category: str
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    status: str


class CommentIn(BaseModel):
    entity_type: str
    entity_id: uuid.UUID
    body: str
    mentions: list[str] = []


class CommentOut(IdMixin):
    entity_type: str
    entity_id: uuid.UUID
    author_id: uuid.UUID | None = None
    author_name: str | None = None
    body: str
    mentions: list = []


class AuditOut(IdMixin):
    occurred_at: datetime
    actor_email: str | None = None
    action: str
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    metadata_json: dict = {}
