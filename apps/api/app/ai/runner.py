"""Execute an AI job: run feature, validate citations, persist results."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.features import run_feature
from app.core.deps import Principal
from app.core.enums import AIJobStatus, AIOutputStatus
from app.models.ai import AICitation, AIFeature, AIJob, AIOutput, AIUsageLedger
from app.services import audit


def run_job(db: Session, principal: Principal, job: AIJob) -> AIOutput:
    """Run a queued AI job synchronously (worker calls this too)."""
    feature = db.scalar(
        select(AIFeature).where(
            AIFeature.organization_id == principal.organization_id,
            AIFeature.code == job.feature_code,
        )
    )
    requires_citations = feature.requires_citations if feature else True

    job.status = AIJobStatus.RUNNING
    job.started_at = datetime.now(tz=UTC)
    job.provider = "mock"
    db.flush()

    try:
        result = run_feature(job.feature_code, db, principal, job.entity_id, job.options or {})
    except Exception as exc:  # noqa: BLE001
        job.status = AIJobStatus.FAILED
        job.error = str(exc)[:1000]
        job.finished_at = datetime.now(tz=UTC)
        db.flush()
        raise

    # Guardrail: fact-based features must cite sources or declare insufficiency.
    is_factual = result.output_type in {"SUMMARY", "FINDINGS", "DUPLICATES"}
    if (
        requires_citations
        and is_factual
        and not result.citations
        and not result.insufficient_evidence
    ):
        # No evidence available -> do not present inference as fact.
        result.insufficient_evidence = True
        result.content_json.setdefault("limitations", []).append(
            "Không đủ nguồn trích dẫn — kết quả được đánh dấu cần kiểm tra."
        )

    output = AIOutput(
        organization_id=principal.organization_id,
        job_id=job.id,
        output_type=result.output_type,
        content_json=result.content_json,
        confidence=result.confidence,
        insufficient_evidence=result.insufficient_evidence,
        human_status=AIOutputStatus.DRAFT,
    )
    db.add(output)
    db.flush()

    for c in result.citations:
        db.add(
            AICitation(
                organization_id=principal.organization_id,
                output_id=output.id,
                citation_id=c.get("citation_id", "c"),
                document_id=_as_uuid(c.get("document_id")),
                chunk_id=_as_uuid(c.get("chunk_id")),
                excerpt=c.get("excerpt"),
                relevance_score=c.get("relevance_score"),
            )
        )

    job.status = AIJobStatus.PARTIAL if result.insufficient_evidence else AIJobStatus.SUCCEEDED
    job.finished_at = datetime.now(tz=UTC)
    db.add(
        AIUsageLedger(
            organization_id=principal.organization_id,
            job_id=job.id,
            feature_code=job.feature_code,
            model_id=job.model_id or "mock-llm-1",
            input_tokens=0,
            output_tokens=0,
            estimated_cost=0,
        )
    )
    audit.record(
        db,
        action="ai.job.run",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="ai_job",
        entity_id=job.id,
        metadata={"feature": job.feature_code},
    )
    db.flush()
    return output


def _as_uuid(val) -> uuid.UUID | None:
    if not val:
        return None
    try:
        return uuid.UUID(str(val))
    except (ValueError, TypeError):
        return None
