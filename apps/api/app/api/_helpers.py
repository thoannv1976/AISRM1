"""Small shared helpers for routers."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.deps import Principal
from app.core.errors import EntityVersionConflict, NotFound


def get_org_scoped(db: Session, model, entity_id: uuid.UUID, principal: Principal):
    """Fetch a record and enforce it belongs to the principal's organization."""
    obj = db.get(model, entity_id)
    if obj is None or getattr(obj, "organization_id", None) != principal.organization_id:
        raise NotFound(f"Không tìm thấy {model.__name__}.")
    return obj


def check_version(obj, expected: int | None) -> None:
    if expected is not None and getattr(obj, "version", None) != expected:
        raise EntityVersionConflict()


def apply_updates(obj, data: dict) -> None:
    for key, value in data.items():
        if key == "version":
            continue
        if value is not None and hasattr(obj, key):
            setattr(obj, key, value)
    if hasattr(obj, "version") and obj.version is not None:
        obj.version += 1
