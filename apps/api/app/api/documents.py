"""Document platform endpoints: upload sessions, storage, versions, search."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.api._helpers import get_org_scoped
from app.core.config import settings
from app.core.db import get_db
from app.core.deps import Principal, get_principal, require
from app.core.enums import Classification, DocumentStatus
from app.core.errors import NotFound, ValidationFailed
from app.core.pagination import Page, PageParams, build_page, page_params, paginate
from app.models.documents import Document, DocumentText, DocumentVersion
from app.schemas.documents import (
    CompleteUploadIn,
    DocumentOut,
    DocumentVersionOut,
    DownloadUrlOut,
    SearchHit,
    SearchOut,
    UploadSessionIn,
    UploadSessionOut,
)
from app.services import audit
from app.services.documents import process_version
from app.services.storage import build_storage_key, get_storage, sha256_bytes
from app.services.tasks import get_queue

router = APIRouter()


@router.get("", response_model=Page[DocumentOut])
def list_documents(
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    params: PageParams = Depends(page_params),
    principal: Principal = Depends(require("documents.read")),
) -> Page[DocumentOut]:
    stmt = select(Document).where(Document.organization_id == principal.organization_id)
    if entity_type:
        stmt = stmt.where(Document.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(Document.entity_id == entity_id)
    stmt = stmt.order_by(Document.created_at.desc())
    items, total = paginate(db, stmt, params)
    return build_page([DocumentOut.model_validate(i) for i in items], total, params)


@router.post("/upload-sessions", response_model=UploadSessionOut, status_code=201)
def create_upload_session(
    payload: UploadSessionIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("documents.create")),
) -> UploadSessionOut:
    if payload.classification not in set(Classification):
        raise ValidationFailed("Phân loại không hợp lệ.")
    doc = Document(
        organization_id=principal.organization_id,
        title=payload.title,
        document_type=payload.document_type,
        classification=payload.classification,
        owner_id=principal.id,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        link_role=payload.link_role,
        status=DocumentStatus.UPLOADING,
        created_by=principal.id,
    )
    db.add(doc)
    db.flush()
    storage_key = build_storage_key(
        principal.organization_id,
        payload.entity_type,
        payload.entity_id,
        doc.id,
        1,
        payload.filename,
    )
    version = DocumentVersion(
        organization_id=principal.organization_id,
        document_id=doc.id,
        version_no=1,
        storage_key=storage_key,
        filename=payload.filename,
        mime_type=payload.mime_type,
        size_bytes=payload.size_bytes,
    )
    db.add(version)
    db.flush()
    doc.current_version_id = version.id
    upload = get_storage().create_upload_url(storage_key, content_type=payload.mime_type)
    return UploadSessionOut(
        document_id=doc.id,
        version_id=version.id,
        upload_url=upload["upload_url"],
        storage_key=storage_key,
        method=upload["method"],
        fields=upload["fields"],
    )


@router.post("/{document_id}/complete-upload", response_model=DocumentOut)
def complete_upload(
    document_id: uuid.UUID,
    payload: CompleteUploadIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("documents.create")),
) -> DocumentOut:
    doc = get_org_scoped(db, Document, document_id, principal)
    version = db.get(DocumentVersion, doc.current_version_id)
    if not version:
        raise NotFound("Phiên bản tài liệu không tồn tại.")
    storage = get_storage()
    if not storage.exists(version.storage_key):
        raise ValidationFailed("Chưa nhận được tệp tải lên.")
    version.uploaded_at = datetime.now(tz=UTC)
    if payload.sha256:
        version.sha256 = payload.sha256
    doc.status = DocumentStatus.QUARANTINED
    db.flush()
    # local/dev: run the pipeline inline (same tx); redis: enqueue for the worker.
    if settings.task_driver.lower() == "redis":
        get_queue().enqueue("document.process", {"document_version_id": str(version.id)})
    else:
        process_version(db, version)
    audit.record(
        db,
        action="document.upload",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="document",
        entity_id=doc.id,
    )
    return DocumentOut.model_validate(doc)


@router.get("/{document_id}/versions", response_model=list[DocumentVersionOut])
def list_versions(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("documents.read")),
) -> list[DocumentVersionOut]:
    get_org_scoped(db, Document, document_id, principal)
    rows = db.scalars(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document_id)
        .order_by(DocumentVersion.version_no.desc())
    ).all()
    return [DocumentVersionOut.model_validate(v) for v in rows]


@router.get("/{document_id}/download-url", response_model=DownloadUrlOut)
def get_download_url(
    document_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("documents.read")),
) -> DownloadUrlOut:
    doc = get_org_scoped(db, Document, document_id, principal)
    version = db.get(DocumentVersion, doc.current_version_id)
    if not version:
        raise NotFound("Không có phiên bản tài liệu.")
    if doc.status == DocumentStatus.QUARANTINED:
        raise ValidationFailed("Tài liệu đang cách ly, chưa thể tải.")
    url = get_storage().download_url(version.storage_key, version.filename, expires_in=300)
    audit.record(
        db,
        action="document.download",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="document",
        entity_id=doc.id,
    )
    return DownloadUrlOut(url=url, expires_in=300, filename=version.filename)


@router.get("/search", response_model=SearchOut)
def search_documents(
    q: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("documents.read")),
) -> SearchOut:
    """Permission-scoped full-text search over extracted document text."""
    like = f"%{q.lower()}%"
    rows = db.execute(
        select(Document, DocumentText)
        .join(DocumentVersion, DocumentVersion.document_id == Document.id)
        .join(DocumentText, DocumentText.document_version_id == DocumentVersion.id)
        .where(
            Document.organization_id == principal.organization_id,
            Document.status == DocumentStatus.AVAILABLE,
            text("lower(document_texts.content) LIKE :like").bindparams(like=like),
        )
        .limit(20)
    ).all()
    hits = []
    for doc, dt in rows:
        idx = (dt.content or "").lower().find(q.lower())
        snippet = (dt.content or "")[max(0, idx - 60) : idx + 120] if idx >= 0 else None
        hits.append(SearchHit(document_id=doc.id, title=doc.title, snippet=snippet, score=1.0))
    return SearchOut(hits=hits, mode="fulltext")


# ----- Internal storage endpoints (local driver only) -----
@router.put("/_storage/{token}")
async def storage_put(
    token: str,
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_principal),
) -> dict:
    """Receive an uploaded object (local driver). Auth required."""
    from app.services.storage import LocalStorage

    storage = get_storage()
    if not isinstance(storage, LocalStorage):
        raise ValidationFailed("Endpoint chỉ dùng cho local storage driver.")
    storage_key = LocalStorage.decode_token(token)
    if f"organizations/{principal.organization_id}" not in storage_key:
        raise ValidationFailed("Storage key ngoài phạm vi tổ chức.")
    data = await request.body()
    storage.save(storage_key, data)
    return {"ok": True, "size": len(data), "sha256": sha256_bytes(data)}


@router.get("/_storage/{token}")
def storage_get(
    token: str,
    exp: int = 0,
    sig: str = "",
    filename: str = "download",
) -> Response:
    """Serve an object via a short-lived signed URL (local driver)."""
    from app.services.storage import LocalStorage

    storage = get_storage()
    if not isinstance(storage, LocalStorage):
        raise NotFound("Không khả dụng.")
    if not LocalStorage.verify_download_sig(token, exp, sig):
        raise NotFound("Liên kết tải đã hết hạn hoặc không hợp lệ.")
    storage_key = LocalStorage.decode_token(token)
    if not storage.exists(storage_key):
        raise NotFound("Tệp không tồn tại.")
    data = storage.read(storage_key)
    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
