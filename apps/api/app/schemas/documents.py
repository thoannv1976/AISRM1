"""Document platform schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import IdMixin


class UploadSessionIn(BaseModel):
    title: str
    filename: str
    mime_type: str | None = None
    classification: str = "INTERNAL"
    document_type: str = "GENERAL"
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    link_role: str | None = None
    size_bytes: int | None = None


class UploadSessionOut(BaseModel):
    document_id: uuid.UUID
    version_id: uuid.UUID
    upload_url: str
    storage_key: str
    method: str = "PUT"
    fields: dict = {}


class CompleteUploadIn(BaseModel):
    sha256: str | None = None
    size_bytes: int | None = None


class DocumentOut(IdMixin):
    organization_id: uuid.UUID
    title: str
    document_type: str
    classification: str
    entity_type: str | None = None
    entity_id: uuid.UUID | None = None
    status: str
    current_version_id: uuid.UUID | None = None


class DocumentVersionOut(IdMixin):
    document_id: uuid.UUID
    version_no: int
    filename: str
    mime_type: str | None = None
    size_bytes: int | None = None
    sha256: str | None = None
    scan_status: str
    extraction_status: str
    uploaded_at: datetime | None = None


class DownloadUrlOut(BaseModel):
    url: str
    expires_in: int
    filename: str


class SearchHit(BaseModel):
    document_id: uuid.UUID
    title: str
    snippet: str | None = None
    score: float | None = None


class SearchOut(BaseModel):
    hits: list[SearchHit]
    mode: str
