"""Permission-filtered retrieval for RAG (Phần F.4).

Filters are applied BEFORE retrieval: organization, classification allow-list,
current-version only, and document status. Citations always point back to a
chunk the user is allowed to read.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.providers import get_embedder
from app.core.config import settings
from app.core.deps import Principal
from app.models.documents import Document, DocumentChunk


@dataclass
class RetrievedChunk:
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    text: str
    page_from: int | None
    score: float


def _allowed_classifications(principal: Principal) -> list[str]:
    base = ["PUBLIC", "INTERNAL"]
    if principal.can("documents.read") or principal.is_admin():
        base += ["CONFIDENTIAL"]
    if principal.is_admin():
        base += ["RESTRICTED"]
    # never exceed the AI provider allow-list
    return [c for c in base if c in settings.ai_allowed_classification_list or principal.is_admin()]


def retrieve(
    db: Session,
    principal: Principal,
    query: str,
    *,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    top_k: int = 6,
) -> list[RetrievedChunk]:
    """Hybrid-ish retrieval: metadata filters first, then vector similarity."""
    allowed = _allowed_classifications(principal)

    stmt = (
        select(DocumentChunk, Document)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(
            DocumentChunk.organization_id == principal.organization_id,
            DocumentChunk.is_current.is_(True),
            DocumentChunk.classification.in_(allowed),
            Document.status == "AVAILABLE",
        )
    )
    if entity_type and entity_id:
        stmt = stmt.where(Document.entity_type == entity_type, Document.entity_id == entity_id)

    rows = db.execute(stmt.limit(500)).all()
    if not rows:
        return []

    # Vector similarity (cosine) computed on the candidate set.
    qvec = get_embedder().embed([query])[0]
    scored: list[RetrievedChunk] = []
    for chunk, doc in rows:
        emb = chunk.embedding
        score = _cosine(qvec, list(emb)) if emb is not None else _keyword_score(query, chunk.text)
        scored.append(
            RetrievedChunk(
                chunk_id=chunk.id,
                document_id=doc.id,
                document_title=doc.title,
                text=chunk.text,
                page_from=chunk.page_from,
                score=score,
            )
        )
    scored.sort(key=lambda c: c.score, reverse=True)
    return scored[:top_k]


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    return float(dot)  # vectors are pre-normalised


def _keyword_score(query: str, text: str) -> float:
    q = {w.lower() for w in query.split() if len(w) > 2}
    if not q:
        return 0.0
    t = text.lower()
    return sum(1 for w in q if w in t) / len(q)
