"""Document platform: documents, versions, chunks, embeddings, access grants."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import BaseModel
from app.core.config import settings
from app.core.enums import Classification, DocumentStatus, ScanStatus

try:  # pgvector is required in real envs; degrade gracefully for tooling
    from pgvector.sqlalchemy import Vector

    _VECTOR = Vector(settings.embedding_dim)
except Exception:  # pragma: no cover
    from sqlalchemy import JSON as _JSON

    _VECTOR = _JSON()


class Document(BaseModel):
    """Metadata only — original files live in object storage."""

    __tablename__ = "documents"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    title: Mapped[str] = mapped_column(String(500))
    document_type: Mapped[str] = mapped_column(String(50), default="GENERAL")
    classification: Mapped[str] = mapped_column(
        String(20), default=Classification.INTERNAL, index=True
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    owner_unit_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    # polymorphic link to a business entity
    entity_type: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, index=True
    )
    link_role: Mapped[str | None] = mapped_column(String(40), nullable=True)
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default=DocumentStatus.UPLOADING, index=True)
    retention_class: Mapped[str | None] = mapped_column(String(40), nullable=True)


class DocumentVersion(BaseModel):
    """Immutable object version with checksum/scan status."""

    __tablename__ = "document_versions"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("documents.id"), index=True
    )
    version_no: Mapped[int] = mapped_column(Integer, default=1)
    storage_key: Mapped[str] = mapped_column(String(800))
    filename: Mapped[str] = mapped_column(String(500))
    mime_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(80), nullable=True)
    scan_status: Mapped[str] = mapped_column(String(20), default=ScanStatus.PENDING)
    extraction_status: Mapped[str] = mapped_column(String(20), default="PENDING")
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DocumentText(BaseModel):
    """Extracted full text (for full-text search) per document version."""

    __tablename__ = "document_texts"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    document_version_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("document_versions.id"), index=True
    )
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSONB, default=dict)


class DocumentChunk(BaseModel):
    """RAG source chunk with access-scope hash for permission-safe retrieval."""

    __tablename__ = "document_chunks"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    document_version_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    chunk_no: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text)
    page_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_to: Mapped[int | None] = mapped_column(Integer, nullable=True)
    heading_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    classification: Mapped[str] = mapped_column(String(20), default=Classification.INTERNAL)
    access_scope_hash: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    embedding = mapped_column(_VECTOR, nullable=True)


class DocumentAccessGrant(BaseModel):
    __tablename__ = "document_access_grants"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("documents.id"), index=True
    )
    grantee_type: Mapped[str] = mapped_column(String(20))  # USER|ROLE|UNIT
    grantee_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True))
    permission: Mapped[str] = mapped_column(String(20), default="READ")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
