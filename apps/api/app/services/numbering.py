"""Simple human-readable code generation for business entities."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session


def next_code(db: Session, model, prefix: str, organization_id: uuid.UUID) -> str:
    year = datetime.now(tz=UTC).year
    count = (
        db.scalar(
            select(func.count()).select_from(model).where(model.organization_id == organization_id)
        )
        or 0
    )
    return f"{prefix}-{year}-{count + 1:04d}"
