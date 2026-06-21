"""KPI runs (reproducible, frozen) and reward applications (M12).

KPI runs compute points from VERIFIED outputs using a versioned points rule;
same data + rule ⇒ same result. Rewards follow an approval workflow.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api._helpers import get_org_scoped
from app.core.db import get_db
from app.core.deps import Principal, require
from app.core.enums import KPIRunStatus, RewardStatus
from app.core.errors import InvalidStateTransition
from app.core.pagination import Page, PageParams, build_page, page_params, paginate
from app.models.outputs import OutputAuthor, ResearchOutput
from app.models.research_extra import KPIContribution, KPIRun, RewardApplication
from app.schemas.common import IdMixin
from app.services import audit
from app.services.numbering import next_code

router = APIRouter()

DEFAULT_POINTS = {
    "JOURNAL_ARTICLE": 1.0,
    "CONFERENCE_PAPER": 0.5,
    "BOOK": 2.0,
    "CHAPTER": 0.75,
    "DATASET": 0.5,
    "SOFTWARE": 0.5,
    "PATENT": 2.0,
    "POLICY_BRIEF": 0.5,
}
_DEFAULT_PT = 0.5


class KPIRunIn(BaseModel):
    period: str = str(datetime.now(tz=UTC).year)
    points: dict[str, float] | None = None


class KPIRunOut(IdMixin):
    organization_id: uuid.UUID
    period: str
    status: str
    total_points: Decimal
    rule_hash: str | None = None
    frozen_at: datetime | None = None


class RewardIn(BaseModel):
    title: str
    output_id: uuid.UUID | None = None
    points: Decimal = Decimal(0)
    amount: Decimal = Decimal(0)
    currency: str = "VND"


class RewardTransitionIn(BaseModel):
    target_status: str
    note: str | None = None


class RewardOut(IdMixin):
    organization_id: uuid.UUID
    code: str
    title: str
    points: Decimal
    amount: Decimal
    currency: str
    status: str


# ----- KPI runs -----
@router.post("/kpi-runs", response_model=KPIRunOut, status_code=201)
def create_kpi_run(
    payload: KPIRunIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("kpi.run")),
) -> KPIRunOut:
    points_map = {**DEFAULT_POINTS, **(payload.points or {})}
    rule_hash = (
        "sha256:" + hashlib.sha256(json.dumps(points_map, sort_keys=True).encode()).hexdigest()[:32]
    )

    run = KPIRun(
        organization_id=principal.organization_id,
        period=payload.period,
        rule_hash=rule_hash,
        status=KPIRunStatus.FROZEN,
        frozen_at=datetime.now(tz=UTC),
    )
    db.add(run)
    db.flush()

    # Verified outputs in scope -> per-author equal share.
    rows = db.execute(
        select(ResearchOutput, OutputAuthor)
        .join(OutputAuthor, OutputAuthor.output_id == ResearchOutput.id)
        .where(
            ResearchOutput.organization_id == principal.organization_id,
            ResearchOutput.verification_status == "VERIFIED",
        )
    ).all()
    author_counts: dict[uuid.UUID, int] = {}
    for out, _ in rows:
        author_counts[out.id] = author_counts.get(out.id, 0) + 1

    total = Decimal(0)
    for out, author in rows:
        base = points_map.get(out.output_type, _DEFAULT_PT)
        share = Decimal(str(round(base / max(author_counts[out.id], 1), 3)))
        db.add(
            KPIContribution(
                organization_id=principal.organization_id,
                run_id=run.id,
                researcher_id=author.researcher_id,
                researcher_name=author.author_name,
                output_id=out.id,
                points=share,
                detail_json={
                    "output_type": out.output_type,
                    "base": base,
                    "authors": author_counts[out.id],
                },
            )
        )
        total += share
    run.total_points = total
    audit.record(
        db,
        action="kpi.run",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="kpi_run",
        entity_id=run.id,
        metadata={"period": payload.period, "total_points": str(total)},
    )
    db.flush()
    return KPIRunOut.model_validate(run)


@router.get("/kpi-runs", response_model=Page[KPIRunOut])
def list_kpi_runs(
    db: Session = Depends(get_db),
    params: PageParams = Depends(page_params),
    principal: Principal = Depends(require("kpi.read")),
) -> Page[KPIRunOut]:
    stmt = (
        select(KPIRun)
        .where(KPIRun.organization_id == principal.organization_id)
        .order_by(KPIRun.created_at.desc())
    )
    items, total = paginate(db, stmt, params)
    return build_page([KPIRunOut.model_validate(i) for i in items], total, params)


@router.get("/kpi-runs/{run_id}")
def get_kpi_run(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("kpi.read")),
) -> dict:
    run = get_org_scoped(db, KPIRun, run_id, principal)
    contribs = db.execute(
        select(
            KPIContribution.researcher_name,
            func.sum(KPIContribution.points),
            func.count(KPIContribution.id),
        )
        .where(KPIContribution.run_id == run.id)
        .group_by(KPIContribution.researcher_name)
        .order_by(func.sum(KPIContribution.points).desc())
    ).all()
    return {
        "run": KPIRunOut.model_validate(run).model_dump(mode="json"),
        "contributions": [
            {"researcher": name, "points": float(pts), "outputs": int(cnt)}
            for name, pts, cnt in contribs
        ],
    }


# ----- Rewards -----
REWARD_TRANSITIONS = {
    RewardStatus.DRAFT: {RewardStatus.SUBMITTED},
    RewardStatus.SUBMITTED: {RewardStatus.UNIT_CONFIRMED, RewardStatus.REJECTED},
    RewardStatus.UNIT_CONFIRMED: {RewardStatus.OFFICE_REVIEWED, RewardStatus.REJECTED},
    RewardStatus.OFFICE_REVIEWED: {RewardStatus.APPROVED, RewardStatus.REJECTED},
    RewardStatus.APPROVED: {RewardStatus.PAID},
}


@router.get("/reward-applications", response_model=Page[RewardOut])
def list_rewards(
    db: Session = Depends(get_db),
    params: PageParams = Depends(page_params),
    principal: Principal = Depends(require("rewards.read")),
) -> Page[RewardOut]:
    stmt = (
        select(RewardApplication)
        .where(RewardApplication.organization_id == principal.organization_id)
        .order_by(RewardApplication.created_at.desc())
    )
    items, total = paginate(db, stmt, params)
    return build_page([RewardOut.model_validate(i) for i in items], total, params)


@router.post("/reward-applications", response_model=RewardOut, status_code=201)
def create_reward(
    payload: RewardIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("rewards.create", "rewards.update")),
) -> RewardOut:
    r = RewardApplication(
        organization_id=principal.organization_id,
        code=next_code(db, RewardApplication, "RW", principal.organization_id),
        applicant_id=principal.id,
        status=RewardStatus.DRAFT,
        **payload.model_dump(),
    )
    db.add(r)
    db.flush()
    audit.record(
        db,
        action="reward.create",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="reward",
        entity_id=r.id,
    )
    return RewardOut.model_validate(r)


@router.post("/reward-applications/{reward_id}/transition", response_model=RewardOut)
def transition_reward(
    reward_id: uuid.UUID,
    payload: RewardTransitionIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("rewards.update", "rewards.approve")),
) -> RewardOut:
    r = get_org_scoped(db, RewardApplication, reward_id, principal)
    allowed = REWARD_TRANSITIONS.get(r.status, set())
    if payload.target_status not in allowed:
        raise InvalidStateTransition(f"Không thể chuyển {r.status} → {payload.target_status}.")
    # Final approval / payment require elevated permission.
    if payload.target_status in {RewardStatus.APPROVED, RewardStatus.PAID} and not principal.can(
        "rewards.approve"
    ):
        raise InvalidStateTransition("Cần quyền rewards.approve để phê duyệt/chi.")
    r.status = payload.target_status
    r.note = payload.note
    if payload.target_status in {RewardStatus.APPROVED, RewardStatus.PAID}:
        r.decided_by = principal.id
    audit.record(
        db,
        action="reward.transition",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="reward",
        entity_id=r.id,
        metadata={"to": payload.target_status},
    )
    return RewardOut.model_validate(r)
