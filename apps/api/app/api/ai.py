"""AI Research Copilot endpoints (suggestion-only, human-in-the-loop)."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.prompts import SYSTEM_CONTRACT
from app.ai.providers import get_llm, set_llm_override
from app.ai.rag import retrieve
from app.ai.runner import run_job
from app.api._helpers import get_org_scoped
from app.core.db import get_db
from app.core.deps import Principal, require
from app.core.enums import AIOutputStatus
from app.core.errors import AIFeatureDisabled
from app.core.pagination import Page, PageParams, build_page, page_params, paginate
from app.models.ai import AICitation, AIFeature, AIFeedback, AIJob, AIOutput, AIUsageLedger
from app.schemas.ai import (
    AIConfigIn,
    AIConfigOut,
    AIJobCreate,
    AIJobOut,
    AIOutputOut,
    AITestOut,
    AIUsageOut,
    ChatIn,
    ChatOut,
    CitationOut,
    FeatureOut,
    FeatureToggleIn,
    FeedbackIn,
)
from app.services import ai_config, audit

router = APIRouter()


@router.get("/features", response_model=list[FeatureOut])
def list_features(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("ai.run", "ai.read")),
) -> list[FeatureOut]:
    rows = db.scalars(
        select(AIFeature)
        .where(AIFeature.organization_id == principal.organization_id)
        .order_by(AIFeature.code)
    ).all()
    return [FeatureOut.model_validate(f) for f in rows]


# ---------------------------------------------------------------------------
# AI configuration & key management (admin)
# ---------------------------------------------------------------------------
@router.get("/config", response_model=AIConfigOut)
def get_ai_config(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("admin.config")),
) -> AIConfigOut:
    setting = ai_config.get_setting(db, principal.organization_id)
    return AIConfigOut(**ai_config.masked(setting))


@router.put("/config", response_model=AIConfigOut)
def save_ai_config(
    payload: AIConfigIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("admin.config")),
) -> AIConfigOut:
    setting = ai_config.get_setting(db, principal.organization_id)
    ai_config.save_config(
        db,
        setting,
        mode=payload.mode,
        provider=payload.provider,
        llm_model=payload.llm_model,
        monthly_budget=payload.monthly_budget,
        api_key=payload.api_key,
        clear_key=payload.clear_key,
    )
    # Audit the change WITHOUT the key value.
    audit.record(
        db,
        action="ai.config.save",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="ai_setting",
        entity_id=setting.id,
        metadata={
            "mode": setting.mode,
            "provider": setting.provider,
            "model": setting.llm_model,
            "key_changed": bool(payload.api_key) or payload.clear_key,
        },
    )
    return AIConfigOut(**ai_config.masked(setting))


@router.post("/config/test", response_model=AITestOut)
def test_ai_config(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("admin.config")),
) -> AITestOut:
    setting = ai_config.get_setting(db, principal.organization_id)
    result = ai_config.test_connection(db, setting)
    audit.record(
        db,
        action="ai.config.test",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="ai_setting",
        entity_id=setting.id,
        metadata={"ok": result["ok"]},
    )
    return AITestOut(**result)


@router.get("/usage", response_model=AIUsageOut)
def get_ai_usage(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("ai.read", "admin.config")),
) -> AIUsageOut:
    return AIUsageOut(**ai_config.usage_summary(db, principal.organization_id))


@router.patch("/features/{feature_id}/toggle", response_model=FeatureOut)
def toggle_feature(
    feature_id: uuid.UUID,
    payload: FeatureToggleIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("admin.config")),
) -> FeatureOut:
    feature = get_org_scoped(db, AIFeature, feature_id, principal)
    feature.enabled = payload.enabled
    audit.record(
        db,
        action="ai.feature.toggle",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="ai_feature",
        entity_id=feature.id,
        metadata={"enabled": payload.enabled, "code": feature.code},
    )
    return FeatureOut.model_validate(feature)


@router.post("/jobs", response_model=AIOutputOut, status_code=201)
def create_job(
    payload: AIJobCreate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("ai.run")),
) -> AIOutputOut:
    feature = db.scalar(
        select(AIFeature).where(
            AIFeature.organization_id == principal.organization_id,
            AIFeature.code == payload.feature_code,
        )
    )
    if feature and not feature.enabled:
        raise AIFeatureDisabled(f"Tính năng {payload.feature_code} đang tắt.")

    input_hash = hashlib.sha256(
        f"{payload.feature_code}|{payload.entity_id}|{payload.options}".encode()
    ).hexdigest()[:32]
    job = AIJob(
        organization_id=principal.organization_id,
        feature_code=payload.feature_code,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        requester_id=principal.id,
        language=payload.language,
        model_id="mock-llm-1",
        input_hash=input_hash,
        options=payload.options,
    )
    db.add(job)
    db.flush()
    # Local/dev: run synchronously. Production enqueues to the worker queue.
    output = run_job(db, principal, job)
    return _output_with_citations(db, output)


@router.get("/jobs", response_model=Page[AIJobOut])
def list_jobs(
    db: Session = Depends(get_db),
    params: PageParams = Depends(page_params),
    principal: Principal = Depends(require("ai.run", "ai.read")),
) -> Page[AIJobOut]:
    stmt = (
        select(AIJob)
        .where(AIJob.organization_id == principal.organization_id)
        .order_by(AIJob.created_at.desc())
    )
    items, total = paginate(db, stmt, params)
    return build_page([AIJobOut.model_validate(i) for i in items], total, params)


@router.get("/jobs/{job_id}", response_model=AIJobOut)
def get_job(
    job_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("ai.run", "ai.read")),
) -> AIJobOut:
    return AIJobOut.model_validate(get_org_scoped(db, AIJob, job_id, principal))


@router.get("/outputs/{output_id}", response_model=AIOutputOut)
def get_output(
    output_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("ai.run", "ai.read")),
) -> AIOutputOut:
    output = get_org_scoped(db, AIOutput, output_id, principal)
    return _output_with_citations(db, output)


@router.post("/outputs/{output_id}/feedback", response_model=AIOutputOut)
def feedback(
    output_id: uuid.UUID,
    payload: FeedbackIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("ai.run")),
) -> AIOutputOut:
    output = get_org_scoped(db, AIOutput, output_id, principal)
    db.add(
        AIFeedback(
            organization_id=principal.organization_id,
            output_id=output.id,
            user_id=principal.id,
            rating=payload.rating,
            reason=payload.reason,
            reported=payload.report,
        )
    )
    if payload.accept is True:
        output.human_status = AIOutputStatus.ACCEPTED
        output.accepted_by = principal.id
        output.accepted_at = datetime.now(tz=UTC)
    elif payload.accept is False:
        output.human_status = AIOutputStatus.REJECTED
    audit.record(
        db,
        action="ai.feedback",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="ai_output",
        entity_id=output.id,
        metadata={"accept": payload.accept, "reported": payload.report},
    )
    return _output_with_citations(db, output)


@router.post("/chat", response_model=ChatOut)
def chat(
    payload: ChatIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("ai.run")),
) -> ChatOut:
    """RAG question answering with permission-filtered retrieval and citations."""
    chunks = retrieve(
        db, principal, payload.message, entity_type=payload.entity_type, entity_id=payload.entity_id
    )
    if not chunks:
        return ChatOut(
            answer="Không đủ dữ liệu trong phạm vi quyền của bạn để trả lời câu hỏi này.",
            citations=[],
            insufficient_evidence=True,
        )
    context = "\n\n".join(
        f"[c{i + 1}] (từ '{c.document_title}'): {c.text[:500]}" for i, c in enumerate(chunks)
    )
    metered, model = ai_config.resolve_metered_llm(db, principal.organization_id)
    set_llm_override(metered)
    res = get_llm().complete(
        SYSTEM_CONTRACT,
        f"Dựa CHỈ trên ngữ cảnh sau, trả lời câu hỏi và trích dẫn [c#].\n\n"
        f"NGỮ CẢNH:\n{context}\n\nCÂU HỎI: {payload.message}",
    )
    set_llm_override(None)
    db.add(
        AIUsageLedger(
            organization_id=principal.organization_id,
            feature_code="RAG_QA",
            model_id=metered.model_id,
            input_tokens=metered.input_tokens,
            output_tokens=metered.output_tokens,
            estimated_cost=ai_config.estimate_cost(
                metered.model_id, metered.input_tokens, metered.output_tokens
            ),
        )
    )
    citations = [
        CitationOut(
            citation_id=f"c{i + 1}",
            document_id=c.document_id,
            excerpt=c.text[:200],
            relevance_score=round(c.score, 3),
        )
        for i, c in enumerate(chunks)
    ]
    audit.record(
        db,
        action="ai.chat",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        metadata={"q_len": len(payload.message)},
    )
    return ChatOut(answer=res.text, citations=citations, insufficient_evidence=False)


def _output_with_citations(db: Session, output: AIOutput) -> AIOutputOut:
    cites = db.scalars(select(AICitation).where(AICitation.output_id == output.id)).all()
    dto = AIOutputOut.model_validate(output)
    dto.citations = [
        CitationOut(
            citation_id=c.citation_id,
            document_id=c.document_id,
            excerpt=c.excerpt,
            relevance_score=c.relevance_score,
        )
        for c in cites
    ]
    return dto
