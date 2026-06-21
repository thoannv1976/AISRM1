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
    CouncilMember,
    Decision,
    Review,
    ReviewAssignment,
    ReviewerProfile,
    ReviewScore,
    Vote,
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


# ----- Review assignments (reviewer inbox) -----
@router.get("/review-assignments", response_model=Page[AssignmentOut])
def list_assignments(
    proposal_id: uuid.UUID | None = None,
    mine: bool = False,
    db: Session = Depends(get_db),
    params: PageParams = Depends(page_params),
    principal: Principal = Depends(require("reviews.read", "reviews.update")),
) -> Page[AssignmentOut]:
    stmt = select(ReviewAssignment).where(
        ReviewAssignment.organization_id == principal.organization_id
    )
    if proposal_id:
        stmt = stmt.where(ReviewAssignment.proposal_id == proposal_id)
    if mine:
        # reviewer profiles linked to this user
        my_ids = [
            r.id
            for r in db.scalars(
                select(ReviewerProfile).where(ReviewerProfile.user_id == principal.id)
            ).all()
        ]
        stmt = stmt.where(ReviewAssignment.reviewer_id.in_(my_ids or [uuid.uuid4()]))
    stmt = stmt.order_by(ReviewAssignment.created_at.desc())
    items, total = paginate(db, stmt, params)
    return build_page([AssignmentOut.model_validate(i) for i in items], total, params)


@router.get("/review-assignments/{assignment_id}", response_model=AssignmentOut)
def get_assignment(
    assignment_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("reviews.read", "reviews.update")),
) -> AssignmentOut:
    return AssignmentOut.model_validate(
        get_org_scoped(db, ReviewAssignment, assignment_id, principal)
    )


# ----- Council membership & meeting workspace -----
@router.post("/councils/{council_id}/members", status_code=201)
def add_member(
    council_id: uuid.UUID,
    member_name: str,
    role: str = "MEMBER",
    user_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("councils.update")),
) -> dict:
    council = get_org_scoped(db, Council, council_id, principal)
    db.add(
        CouncilMember(
            organization_id=principal.organization_id,
            council_id=council.id,
            member_name=member_name,
            role=role,
            user_id=user_id,
        )
    )
    return {"ok": True}


@router.get("/councils/{council_id}/detail")
def council_detail(
    council_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("councils.read")),
) -> dict:
    c = get_org_scoped(db, Council, council_id, principal)
    members = db.scalars(select(CouncilMember).where(CouncilMember.council_id == c.id)).all()
    meetings = db.scalars(select(CouncilMeeting).where(CouncilMeeting.council_id == c.id)).all()
    return {
        "council": CouncilOut.model_validate(c).model_dump(mode="json"),
        "members": [{"id": str(m.id), "name": m.member_name, "role": m.role} for m in members],
        "meetings": [
            {
                "id": str(m.id),
                "title": m.title,
                "status": m.status,
                "quorum_required": m.quorum_required,
                "meeting_at": m.meeting_at.isoformat() if m.meeting_at else None,
            }
            for m in meetings
        ],
    }


@router.post("/council-meetings/{meeting_id}/votes", status_code=201)
def cast_vote(
    meeting_id: uuid.UUID,
    proposal_id: uuid.UUID,
    vote_value: str,
    score: float | None = None,
    comment: str | None = None,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("councils.update")),
) -> dict:
    meeting = get_org_scoped(db, CouncilMeeting, meeting_id, principal)
    if meeting.status == "FINALIZED":
        raise InvalidStateTransition("Phiên họp đã chốt; không thể bỏ phiếu thêm.")
    db.add(
        Vote(
            organization_id=principal.organization_id,
            meeting_id=meeting.id,
            proposal_id=proposal_id,
            member_id=principal.id,
            vote_value=vote_value,
            score=score,
            comment=comment,
        )
    )
    return {"ok": True}


@router.post("/council-meetings/{meeting_id}/finalize")
def finalize_meeting(
    meeting_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("councils.update")),
) -> dict:
    meeting = get_org_scoped(db, CouncilMeeting, meeting_id, principal)
    if meeting.status == "FINALIZED":
        raise InvalidStateTransition("Phiên họp đã được chốt.")
    votes = db.scalars(select(Vote).where(Vote.meeting_id == meeting.id)).all()
    voters = {v.member_id for v in votes if v.member_id}
    if meeting.quorum_required and len(voters) < meeting.quorum_required:
        raise InvalidStateTransition(f"Chưa đủ quorum ({len(voters)}/{meeting.quorum_required}).")
    # Aggregate per proposal.
    agg: dict[str, dict] = {}
    for v in votes:
        key = str(v.proposal_id)
        a = agg.setdefault(key, {"approve": 0, "reject": 0, "abstain": 0, "scores": []})
        a[v.vote_value.lower()] = a.get(v.vote_value.lower(), 0) + 1
        if v.score is not None:
            a["scores"].append(float(v.score))
    results = []
    for pid, a in agg.items():
        avg = round(sum(a["scores"]) / len(a["scores"]), 2) if a["scores"] else None
        outcome = "APPROVED" if a["approve"] > a["reject"] else "REJECTED"
        results.append({"proposal_id": pid, **a, "avg_score": avg, "consensus": outcome})
        db.add(
            Decision(
                organization_id=principal.organization_id,
                scope_type="proposal",
                scope_id=uuid.UUID(pid),
                decision_type="COUNCIL",
                decision_date=datetime.now(tz=UTC),
                outcome=outcome,
                approved_by=principal.id,
            )
        )
    meeting.status = "FINALIZED"
    audit.record(
        db,
        action="council.finalize",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="council_meeting",
        entity_id=meeting.id,
        metadata={"quorum_voters": len(voters)},
    )
    db.flush()
    return {"ok": True, "results": results, "quorum_voters": len(voters)}
