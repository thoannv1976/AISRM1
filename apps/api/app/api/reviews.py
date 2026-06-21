"""Review, conflict-of-interest, reviewer matching and council endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api._helpers import get_org_scoped
from app.core.db import get_db
from app.core.deps import Principal, require
from app.core.enums import AssignmentStatus, ConflictDecision
from app.core.errors import ConflictOfInterest, InvalidStateTransition
from app.core.pagination import Page, PageParams, build_page, page_params, paginate
from app.models.proposals import Proposal
from app.models.reviews import (
    ConflictDeclaration,
    Council,
    CouncilMeeting,
    Review,
    ReviewAssignment,
    ReviewerProfile,
    ReviewScore,
)
from app.schemas.reviews import (
    AcceptIn,
    AssignIn,
    AssignmentOut,
    ConflictIn,
    CouncilIn,
    CouncilOut,
    MeetingIn,
    ReviewerIn,
    ReviewerOut,
    ReviewOut,
    ReviewSubmitIn,
    SuggestionOut,
)
from app.services import audit
from app.services.matching import suggest_reviewers

router = APIRouter()


# ----- Reviewer pool -----
@router.get("/reviewers", response_model=Page[ReviewerOut])
def list_reviewers(
    db: Session = Depends(get_db),
    params: PageParams = Depends(page_params),
    principal: Principal = Depends(require("reviews.read")),
) -> Page[ReviewerOut]:
    stmt = (
        select(ReviewerProfile)
        .where(ReviewerProfile.organization_id == principal.organization_id)
        .order_by(ReviewerProfile.full_name)
    )
    items, total = paginate(db, stmt, params)
    return build_page([ReviewerOut.model_validate(i) for i in items], total, params)


@router.post("/reviewers", response_model=ReviewerOut, status_code=201)
def create_reviewer(
    payload: ReviewerIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("reviews.create", "reviews.update")),
) -> ReviewerOut:
    r = ReviewerProfile(organization_id=principal.organization_id, **payload.model_dump())
    db.add(r)
    db.flush()
    return ReviewerOut.model_validate(r)


# ----- COI -----
@router.post("/conflict-declarations", status_code=201)
def declare_conflict(
    payload: ConflictIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("reviews.update")),
) -> dict:
    c = ConflictDeclaration(organization_id=principal.organization_id, **payload.model_dump())
    db.add(c)
    audit.record(
        db,
        action="coi.declare",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="reviewer",
        entity_id=payload.reviewer_id,
        metadata={"type": payload.conflict_type},
    )
    return {"ok": True}


# ----- Matching (AI-06) -----
@router.post("/proposals/{proposal_id}/reviewer-suggestions", response_model=list[SuggestionOut])
def reviewer_suggestions(
    proposal_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("reviews.read", "ai.run")),
) -> list[SuggestionOut]:
    get_org_scoped(db, Proposal, proposal_id, principal)
    suggestions = suggest_reviewers(db, principal, proposal_id)
    audit.record(
        db,
        action="reviewer.suggest",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="proposal",
        entity_id=proposal_id,
    )
    return [SuggestionOut(**s) for s in suggestions]


# ----- Assignment -----
@router.post("/review-assignments", response_model=AssignmentOut, status_code=201)
def create_assignment(
    payload: AssignIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("reviews.assign", "reviews.update")),
) -> AssignmentOut:
    proposal = get_org_scoped(db, Proposal, payload.proposal_id, principal)
    # Hard COI guard: block if reviewer has a blocking conflict on this proposal.
    blocking = db.scalar(
        select(ConflictDeclaration).where(
            ConflictDeclaration.proposal_id == proposal.id,
            ConflictDeclaration.reviewer_id == payload.reviewer_id,
            ConflictDeclaration.decision == ConflictDecision.BLOCKED,
        )
    )
    if blocking:
        raise ConflictOfInterest("Reviewer có xung đột lợi ích bị chặn cho hồ sơ này.")

    assignment = ReviewAssignment(
        organization_id=principal.organization_id,
        proposal_id=proposal.id,
        reviewer_id=payload.reviewer_id,
        template_id=payload.template_id,
        assigned_at=datetime.now(tz=UTC),
        due_at=payload.due_at,
        status=AssignmentStatus.INVITED,
        blind_code=f"R{str(uuid.uuid4())[:4].upper()}",
    )
    db.add(assignment)
    reviewer = db.get(ReviewerProfile, payload.reviewer_id)
    if reviewer:
        reviewer.current_load = (reviewer.current_load or 0) + 1
    audit.record(
        db,
        action="review.assign",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="proposal",
        entity_id=proposal.id,
    )
    db.flush()
    return AssignmentOut.model_validate(assignment)


@router.post("/review-assignments/{assignment_id}/accept", response_model=AssignmentOut)
def accept_assignment(
    assignment_id: uuid.UUID,
    payload: AcceptIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("reviews.update")),
) -> AssignmentOut:
    assignment = get_org_scoped(db, ReviewAssignment, assignment_id, principal)
    if payload.coi_declared:
        db.add(
            ConflictDeclaration(
                organization_id=principal.organization_id,
                reviewer_id=assignment.reviewer_id,
                proposal_id=assignment.proposal_id,
                conflict_type="OTHER",
                details="Tự khai khi nhận lời mời",
                decision=ConflictDecision.DECLARED,
            )
        )
        assignment.status = AssignmentStatus.DECLINED
    elif payload.accept:
        # Reviewer cannot see the proposal before accepting confidentiality/COI.
        if not payload.confidentiality_accepted:
            raise InvalidStateTransition("Phải chấp nhận điều khoản bảo mật trước khi nhận.")
        assignment.status = AssignmentStatus.ACCEPTED
        assignment.confidentiality_accepted = True
        assignment.coi_checked = True
    else:
        assignment.status = AssignmentStatus.DECLINED
    audit.record(
        db,
        action="review.accept",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="review_assignment",
        entity_id=assignment.id,
        metadata={"status": assignment.status},
    )
    return AssignmentOut.model_validate(assignment)


@router.post("/review-assignments/{assignment_id}/review", response_model=ReviewOut)
def submit_review(
    assignment_id: uuid.UUID,
    payload: ReviewSubmitIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("reviews.submit")),
) -> ReviewOut:
    assignment = get_org_scoped(db, ReviewAssignment, assignment_id, principal)
    if assignment.status != AssignmentStatus.ACCEPTED:
        raise InvalidStateTransition("Phải nhận lời mời (accept) trước khi chấm.")
    overall = sum((s.score * s.weight for s in payload.scores), start=0)
    weight_sum = sum((s.weight for s in payload.scores), start=0) or 1
    review = Review(
        organization_id=principal.organization_id,
        assignment_id=assignment.id,
        proposal_id=assignment.proposal_id,
        overall_score=round(float(overall) / float(weight_sum), 2),
        recommendation=payload.recommendation,
        applicant_comments=payload.applicant_comments,
        confidential_comments=payload.confidential_comments,
        strengths=payload.strengths,
        weaknesses=payload.weaknesses,
        submitted_at=datetime.now(tz=UTC),
    )
    db.add(review)
    db.flush()
    for s in payload.scores:
        db.add(
            ReviewScore(
                organization_id=principal.organization_id,
                review_id=review.id,
                criterion_code=s.criterion_code,
                score=s.score,
                weight=s.weight,
                comment=s.comment,
            )
        )
    assignment.status = AssignmentStatus.SUBMITTED
    audit.record(
        db,
        action="review.submit",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="review",
        entity_id=review.id,
    )
    return ReviewOut.model_validate(review)


@router.get("/proposals/{proposal_id}/reviews", response_model=list[ReviewOut])
def list_proposal_reviews(
    proposal_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("reviews.read")),
) -> list[ReviewOut]:
    get_org_scoped(db, Proposal, proposal_id, principal)
    rows = db.scalars(select(Review).where(Review.proposal_id == proposal_id)).all()
    return [ReviewOut.model_validate(r) for r in rows]


# ----- Council -----
@router.get("/councils", response_model=Page[CouncilOut])
def list_councils(
    db: Session = Depends(get_db),
    params: PageParams = Depends(page_params),
    principal: Principal = Depends(require("councils.read")),
) -> Page[CouncilOut]:
    stmt = select(Council).where(Council.organization_id == principal.organization_id)
    items, total = paginate(db, stmt, params)
    return build_page([CouncilOut.model_validate(i) for i in items], total, params)


@router.post("/councils", response_model=CouncilOut, status_code=201)
def create_council(
    payload: CouncilIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("councils.create", "councils.update")),
) -> CouncilOut:
    c = Council(organization_id=principal.organization_id, **payload.model_dump())
    db.add(c)
    db.flush()
    return CouncilOut.model_validate(c)


@router.post("/councils/{council_id}/meetings", status_code=201)
def create_meeting(
    council_id: uuid.UUID,
    payload: MeetingIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("councils.update")),
) -> dict:
    council = get_org_scoped(db, Council, council_id, principal)
    m = CouncilMeeting(
        organization_id=principal.organization_id, council_id=council.id, **payload.model_dump()
    )
    db.add(m)
    db.flush()
    return {"ok": True, "meeting_id": str(m.id)}
