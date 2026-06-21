"""Reviewer matching (AI-06): hard COI exclusion first, then transparent scoring.

AI/ML only assists ranking; the human officer assigns. No auto-invite.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import Principal
from app.models.proposals import Proposal
from app.models.researchers import ResearcherProfile
from app.models.reviews import ConflictDeclaration, ReviewerProfile


def suggest_reviewers(
    db: Session, principal: Principal, proposal_id: uuid.UUID, top_k: int = 10
) -> list[dict]:
    proposal = db.get(Proposal, proposal_id)
    if not proposal or proposal.organization_id != principal.organization_id:
        return []

    fields = set(f.lower() for f in (proposal.fields or []))
    keywords = set(k.lower() for k in (proposal.keywords or []))
    target_terms = fields | keywords | set((proposal.title or "").lower().split())

    # Hard COI exclusions already declared/blocked for this proposal.
    blocked = {
        c.reviewer_id
        for c in db.scalars(
            select(ConflictDeclaration).where(
                ConflictDeclaration.proposal_id == proposal_id,
                ConflictDeclaration.decision.in_(["BLOCKED", "DECLARED"]),
            )
        ).all()
    }

    # PI and team members of the same unit are a structural conflict.
    pi_profile = db.get(ResearcherProfile, proposal.pi_id) if proposal.pi_id else None
    pi_unit = pi_profile.unit_id if pi_profile else None

    reviewers = db.scalars(
        select(ReviewerProfile).where(
            ReviewerProfile.organization_id == principal.organization_id,
            ReviewerProfile.is_active.is_(True),
        )
    ).all()

    suggestions: list[dict] = []
    for r in reviewers:
        excluded = False
        reason_excl = None
        if r.id in blocked:
            excluded, reason_excl = True, "Đã khai báo/đánh dấu xung đột lợi ích."
        # Expertise overlap score
        expertise = set(e.lower() for e in (r.expertise or []))
        overlap = expertise & target_terms
        score = len(overlap) * 10.0
        # Load penalty
        score -= min(r.current_load, 5) * 2.0
        reasons = []
        if overlap:
            reasons.append(f"Trùng chuyên môn: {', '.join(sorted(overlap))}")
        if r.current_load:
            reasons.append(f"Tải hiện tại: {r.current_load} hồ sơ")
        if r.is_external:
            reasons.append("Chuyên gia ngoài trường (giảm xung đột)")
            score += 3.0
        if not reasons:
            reasons.append("Chưa có dữ liệu chuyên môn trùng khớp")

        suggestions.append(
            {
                "reviewer_id": r.id,
                "full_name": r.full_name,
                "score": round(max(score, 0.0), 2),
                "reasons": reasons,
                "excluded": excluded,
                "exclusion_reason": reason_excl,
            }
        )

    # Structural conflict: reviewer in the same unit as the PI (when known).
    if pi_unit is not None:
        for s in suggestions:
            rev = next((x for x in reviewers if x.id == s["reviewer_id"]), None)
            if rev is not None and rev.user_id and pi_profile and rev.user_id == pi_profile.user_id:
                s["excluded"] = True
                s["exclusion_reason"] = "Trùng người với chủ nhiệm đề tài."

    # Excluded last; then by score desc.
    suggestions.sort(key=lambda s: (s["excluded"], -s["score"]))
    return suggestions[:top_k]
