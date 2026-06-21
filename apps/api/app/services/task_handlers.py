"""Handlers executed by the worker (or inline via LocalTaskQueue)."""
from __future__ import annotations

import uuid
from typing import Any

from app.core.db import SessionLocal
from app.models.documents import DocumentVersion
from app.services.documents import process_version


def handle(task_type: str, payload: dict[str, Any]) -> None:
    if task_type == "document.process":
        _process_document(payload)
    else:  # unknown task types are ignored (logged in production)
        print(f"[worker] unknown task type: {task_type}")


def _process_document(payload: dict[str, Any]) -> None:
    version_id = payload.get("document_version_id")
    if not version_id:
        return
    db = SessionLocal()
    try:
        version = db.get(DocumentVersion, uuid.UUID(version_id))
        if version:
            process_version(db, version)
            db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
