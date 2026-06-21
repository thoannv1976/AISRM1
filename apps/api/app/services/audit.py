"""Append-only audit logging."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models.identity import AuditLog


def record(
    db: Session,
    *,
    action: str,
    actor_id: uuid.UUID | None = None,
    actor_email: str | None = None,
    organization_id: uuid.UUID | None = None,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    metadata: dict[str, Any] | None = None,
    trace_id: str | None = None,
    ip: str | None = None,
) -> AuditLog:
    """Write an audit entry. Caller's transaction commits it."""
    log = AuditLog(
        occurred_at=datetime.now(tz=UTC),
        action=action,
        actor_id=actor_id,
        actor_email=actor_email,
        organization_id=organization_id,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=metadata or {},
        trace_id=trace_id,
        ip=ip,
    )
    db.add(log)
    return log
