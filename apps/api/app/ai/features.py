"""Grounded AI feature builders.

Each builder reads authorized data, optionally calls the LLM provider for
free-text generation, and returns a structured, citation-bearing result. Even
with the offline mock provider these produce useful, data-grounded output.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.prompts import SYSTEM_CONTRACT
from app.ai.providers import get_llm
from app.core.deps import Principal
from app.models.outputs import ResearchOutput
from app.models.proposals import (
    Deliverable,
    Proposal,
    ProposalBudgetLine,
    ProposalTeamMember,
    WorkPackage,
)
from app.models.researchers import ResearcherProfile


@dataclass
class FeatureResult:
    output_type: str
    content_json: dict
    citations: list[dict] = field(default_factory=list)
    confidence: float | None = None
    insufficient_evidence: bool = False


# ---------------------------------------------------------------------------
# Proposal features
# ---------------------------------------------------------------------------
def _load_proposal(db: Session, principal: Principal, entity_id: uuid.UUID) -> Proposal | None:
    p = db.get(Proposal, entity_id)
    if p and p.organization_id == principal.organization_id:
        return p
    return None


def proposal_summary(
    db: Session, principal: Principal, entity_id: uuid.UUID, opts: dict
) -> FeatureResult:
    p = _load_proposal(db, principal, entity_id)
    if not p:
        return FeatureResult(
            "SUMMARY", {"summary": "", "limitations": []}, insufficient_evidence=True
        )
    content = p.content_json or {}
    body = "\n".join(
        f"{k}: {v}"
        for k, v in {
            "title": p.title,
            "abstract": p.abstract,
            "objectives": content.get("objectives"),
            "methods": content.get("methods"),
            "impact": content.get("impact"),
        }.items()
        if v
    )
    llm = get_llm()
    res = llm.complete(
        SYSTEM_CONTRACT,
        f"Tóm tắt đề xuất nghiên cứu sau bằng tiếng {('Anh' if opts.get('language') == 'en' else 'Việt')}, "
        f"nêu mục tiêu, phương pháp và sản phẩm kỳ vọng:\n\n{body}",
    )
    cite = _cite("c1", f"{p.title} — {p.abstract or ''}"[:300])
    return FeatureResult(
        "SUMMARY",
        {"summary": res.text, "limitations": ["AI gợi ý — cần người kiểm tra."]},
        citations=[cite],
        confidence=0.6,
    )


def proposal_completeness(
    db: Session, principal: Principal, entity_id: uuid.UUID, opts: dict
) -> FeatureResult:
    p = _load_proposal(db, principal, entity_id)
    if not p:
        return FeatureResult("FINDINGS", {"findings": []}, insufficient_evidence=True)
    content = p.content_json or {}
    findings: list[dict] = []
    required = {
        "objectives": "Mục tiêu nghiên cứu",
        "methods": "Phương pháp nghiên cứu",
        "impact": "Tác động dự kiến",
        "data_management": "Kế hoạch quản lý dữ liệu",
    }
    for key, label in required.items():
        if not content.get(key):
            findings.append(
                _finding(
                    "MISSING_SECTION",
                    "MEDIUM",
                    f"Thiếu phần: {label}.",
                    [],
                    f"Bổ sung nội dung cho mục '{label}'.",
                )
            )
    if not p.abstract:
        findings.append(
            _finding(
                "MISSING_ABSTRACT",
                "MEDIUM",
                "Chưa có tóm tắt (abstract).",
                [],
                "Viết tóm tắt 150–300 từ.",
            )
        )
    team = db.scalars(
        select(ProposalTeamMember).where(ProposalTeamMember.proposal_id == p.id)
    ).all()
    if not team:
        findings.append(
            _finding(
                "NO_TEAM",
                "HIGH",
                "Chưa khai báo thành viên nhóm nghiên cứu.",
                [],
                "Thêm ít nhất chủ nhiệm và 1 thành viên.",
            )
        )
    budget = db.scalars(
        select(ProposalBudgetLine).where(ProposalBudgetLine.proposal_id == p.id)
    ).all()
    if not budget:
        findings.append(
            _finding(
                "NO_BUDGET",
                "HIGH",
                "Chưa có dự toán kinh phí.",
                [],
                "Bổ sung các dòng ngân sách theo hạng mục.",
            )
        )
    deliverables = db.scalars(select(Deliverable).where(Deliverable.proposal_id == p.id)).all()
    if not deliverables:
        findings.append(
            _finding(
                "NO_DELIVERABLE",
                "MEDIUM",
                "Chưa khai báo sản phẩm cam kết.",
                [],
                "Thêm deliverables với tiêu chí nghiệm thu.",
            )
        )
    return FeatureResult(
        "FINDINGS",
        {
            "findings": findings,
            "checked": list(required.keys()) + ["team", "budget", "deliverables"],
        },
        confidence=0.9,
    )


def proposal_consistency(
    db: Session, principal: Principal, entity_id: uuid.UUID, opts: dict
) -> FeatureResult:
    p = _load_proposal(db, principal, entity_id)
    if not p:
        return FeatureResult("FINDINGS", {"findings": []}, insufficient_evidence=True)
    findings: list[dict] = []
    wps = db.scalars(select(WorkPackage).where(WorkPackage.proposal_id == p.id)).all()
    deliverables = db.scalars(select(Deliverable).where(Deliverable.proposal_id == p.id)).all()
    budget_lines = db.scalars(
        select(ProposalBudgetLine).where(ProposalBudgetLine.proposal_id == p.id)
    ).all()
    budget_sum = sum((b.amount for b in budget_lines), start=0)

    if wps and not deliverables:
        findings.append(
            _finding(
                "WP_WITHOUT_DELIVERABLE",
                "MEDIUM",
                "Có work packages nhưng không có sản phẩm cam kết tương ứng.",
                [],
                "Gắn mỗi work package với ít nhất một deliverable.",
            )
        )
    if p.budget_total and budget_sum and abs(float(p.budget_total) - float(budget_sum)) > 1:
        findings.append(
            _finding(
                "BUDGET_MISMATCH",
                "HIGH",
                f"Tổng ngân sách ({p.budget_total}) khác tổng các dòng dự toán ({budget_sum}).",
                [],
                "Đối chiếu và cập nhật tổng ngân sách.",
            )
        )
    content = p.content_json or {}
    if content.get("objectives") and not content.get("methods"):
        findings.append(
            _finding(
                "OBJECTIVE_METHOD_GAP",
                "MEDIUM",
                "Có mục tiêu nhưng thiếu phương pháp tương ứng.",
                [],
                "Mô tả phương pháp để đạt từng mục tiêu.",
            )
        )
    return FeatureResult("FINDINGS", {"findings": findings}, confidence=0.85)


def field_sdg_classification(
    db: Session, principal: Principal, entity_id: uuid.UUID, opts: dict
) -> FeatureResult:
    p = _load_proposal(db, principal, entity_id)
    if not p:
        return FeatureResult("CLASSIFICATION", {}, insufficient_evidence=True)
    text = " ".join(filter(None, [p.title, p.abstract] + (p.keywords or []))).lower()
    sdg_map = {
        "3": ["health", "y tế", "sức khỏe", "bệnh"],
        "4": ["education", "giáo dục", "đào tạo", "học"],
        "7": ["energy", "năng lượng", "điện"],
        "9": ["industry", "công nghiệp", "đổi mới", "hạ tầng"],
        "13": ["climate", "khí hậu", "môi trường", "carbon"],
    }
    suggested = [sdg for sdg, kws in sdg_map.items() if any(k in text for k in kws)]
    return FeatureResult(
        "CLASSIFICATION",
        {"suggested_sdgs": suggested, "note": "Gợi ý — người dùng xác nhận trước khi áp dụng."},
        confidence=0.5,
    )


# ---------------------------------------------------------------------------
# Output features
# ---------------------------------------------------------------------------
def duplicate_detection(
    db: Session, principal: Principal, entity_id: uuid.UUID, opts: dict
) -> FeatureResult:
    out = db.get(ResearchOutput, entity_id)
    if not out or out.organization_id != principal.organization_id:
        return FeatureResult("DUPLICATES", {"candidates": []}, insufficient_evidence=True)
    candidates: list[dict] = []
    others = db.scalars(
        select(ResearchOutput).where(
            ResearchOutput.organization_id == principal.organization_id,
            ResearchOutput.id != out.id,
        )
    ).all()
    for o in others:
        if out.doi and o.doi and out.doi.lower() == o.doi.lower():
            candidates.append(
                {
                    "output_id": str(o.id),
                    "title": o.title,
                    "doi": o.doi,
                    "match_type": "DOI",
                    "score": 1.0,
                }
            )
        elif _title_sim(out.title, o.title) > 0.8:
            candidates.append(
                {
                    "output_id": str(o.id),
                    "title": o.title,
                    "doi": o.doi,
                    "match_type": "TITLE",
                    "score": round(_title_sim(out.title, o.title), 2),
                }
            )
    return FeatureResult("DUPLICATES", {"candidates": candidates}, confidence=0.9)


def research_profile_summary(
    db: Session, principal: Principal, entity_id: uuid.UUID, opts: dict
) -> FeatureResult:
    prof = db.get(ResearcherProfile, entity_id)
    if not prof or prof.organization_id != principal.organization_id:
        return FeatureResult("SUMMARY", {"summary": ""}, insufficient_evidence=True)
    body = (
        f"{prof.full_name}; {prof.academic_title or ''} {prof.degree or ''}; "
        f"từ khóa: {', '.join(prof.keywords or [])}; phương pháp: {', '.join(prof.research_methods or [])}"
    )
    res = get_llm().complete(SYSTEM_CONTRACT, f"Tóm tắt năng lực nghiên cứu:\n{body}")
    return FeatureResult(
        "SUMMARY", {"summary": res.text}, confidence=0.55, citations=[_cite("c1", body[:300])]
    )


def generic_feature(
    db: Session, principal: Principal, entity_id: uuid.UUID | None, opts: dict
) -> FeatureResult:
    return FeatureResult(
        "INFO",
        {
            "summary": "Tính năng AI này đã được cấu hình nhưng chưa có builder chuyên biệt.",
            "limitations": ["Không đủ dữ liệu hoặc tính năng đang phát triển."],
        },
        insufficient_evidence=True,
    )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
Builder = Callable[[Session, Principal, uuid.UUID, dict], FeatureResult]

REGISTRY: dict[str, Builder] = {
    "PROPOSAL_SUMMARY": proposal_summary,
    "PROPOSAL_COMPLETENESS": proposal_completeness,
    "PROPOSAL_CONSISTENCY_REVIEW": proposal_consistency,
    "FIELD_SDG_CLASSIFICATION": field_sdg_classification,
    "DUPLICATE_DETECTION": duplicate_detection,
    "RESEARCH_PROFILE_SUMMARY": research_profile_summary,
}


def run_feature(
    code: str, db: Session, principal: Principal, entity_id, opts: dict
) -> FeatureResult:
    builder = REGISTRY.get(code, generic_feature)
    return builder(db, principal, entity_id, opts)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _cite(cid: str, excerpt: str) -> dict:
    return {"citation_id": cid, "excerpt": excerpt, "relevance_score": 0.8}


def _finding(
    code: str, severity: str, statement: str, evidence: list[str], suggestion: str
) -> dict:
    return {
        "code": code,
        "severity": severity,
        "statement": statement,
        "evidence": evidence,
        "suggestion": suggestion,
    }


def _title_sim(a: str, b: str) -> float:
    sa = {w for w in (a or "").lower().split() if len(w) > 2}
    sb = {w for w in (b or "").lower().split() if len(w) > 2}
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)
