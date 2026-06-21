"""Research outputs / publications endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api._helpers import apply_updates, check_version, get_org_scoped
from app.core.db import get_db
from app.core.deps import Principal, require
from app.core.enums import OutputStatus, VerificationStatus
from app.core.errors import ValidationFailed
from app.core.pagination import Page, PageParams, build_page, page_params, paginate
from app.models.outputs import (
    OutputAuthor,
    OutputIdentifier,
    PublicationVenue,
    ResearchOutput,
    Verification,
)
from app.schemas.outputs import (
    DuplicateCandidate,
    DuplicateOut,
    OutputCreate,
    OutputOut,
    OutputUpdate,
    VenueIn,
    VerifyIn,
)
from app.services import audit

router = APIRouter()


def normalize_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    d = doi.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if d.startswith(prefix):
            d = d[len(prefix) :]
    return d or None


@router.get("/research-outputs", response_model=Page[OutputOut])
def list_outputs(
    status: str | None = None,
    output_type: str | None = None,
    year: int | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    params: PageParams = Depends(page_params),
    principal: Principal = Depends(require("outputs.read")),
) -> Page[OutputOut]:
    stmt = select(ResearchOutput).where(ResearchOutput.organization_id == principal.organization_id)
    if status:
        stmt = stmt.where(ResearchOutput.status == status)
    if output_type:
        stmt = stmt.where(ResearchOutput.output_type == output_type)
    if year:
        stmt = stmt.where(ResearchOutput.year == year)
    if q:
        stmt = stmt.where(ResearchOutput.title.ilike(f"%{q}%"))
    stmt = stmt.order_by(ResearchOutput.year.desc().nullslast(), ResearchOutput.created_at.desc())
    items, total = paginate(db, stmt, params)
    return build_page([OutputOut.model_validate(i) for i in items], total, params)


@router.post("/research-outputs", response_model=OutputOut, status_code=201)
def create_output(
    payload: OutputCreate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("outputs.create")),
) -> OutputOut:
    doi = normalize_doi(payload.doi)
    if doi:
        dup = db.scalar(
            select(ResearchOutput).where(
                ResearchOutput.organization_id == principal.organization_id,
                ResearchOutput.doi == doi,
                ResearchOutput.status != OutputStatus.ARCHIVED,
            )
        )
        if dup:
            raise ValidationFailed(f"DOI đã tồn tại cho output khác (id={dup.id}).")
    data = payload.model_dump(exclude={"authors", "doi"})
    output = ResearchOutput(
        organization_id=principal.organization_id, created_by=principal.id, doi=doi, **data
    )
    db.add(output)
    db.flush()
    for a in payload.authors:
        db.add(
            OutputAuthor(
                organization_id=principal.organization_id, output_id=output.id, **a.model_dump()
            )
        )
    if doi:
        db.add(
            OutputIdentifier(
                organization_id=principal.organization_id,
                output_id=output.id,
                type="DOI",
                value=doi,
            )
        )
    audit.record(
        db,
        action="output.create",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="output",
        entity_id=output.id,
    )
    return OutputOut.model_validate(output)


@router.get("/research-outputs/{output_id}", response_model=OutputOut)
def get_output(
    output_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("outputs.read")),
) -> OutputOut:
    return OutputOut.model_validate(get_org_scoped(db, ResearchOutput, output_id, principal))


@router.patch("/research-outputs/{output_id}", response_model=OutputOut)
def update_output(
    output_id: uuid.UUID,
    payload: OutputUpdate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("outputs.update")),
) -> OutputOut:
    output = get_org_scoped(db, ResearchOutput, output_id, principal)
    check_version(output, payload.version)
    data = payload.model_dump(exclude_unset=True)
    if "doi" in data:
        data["doi"] = normalize_doi(data["doi"])
    apply_updates(output, data)
    audit.record(
        db,
        action="output.update",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="output",
        entity_id=output.id,
    )
    return OutputOut.model_validate(output)


@router.post("/research-outputs/{output_id}/claim", response_model=OutputOut)
def claim_output(
    output_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("outputs.update", "outputs.create")),
) -> OutputOut:
    output = get_org_scoped(db, ResearchOutput, output_id, principal)
    output.status = OutputStatus.CLAIMED
    db.add(
        Verification(
            organization_id=principal.organization_id,
            output_id=output.id,
            step="CLAIM",
            decision="APPROVED",
            verified_by=principal.id,
            decided_at=datetime.now(tz=UTC),
        )
    )
    audit.record(
        db,
        action="output.claim",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="output",
        entity_id=output.id,
    )
    return OutputOut.model_validate(output)


@router.post("/research-outputs/{output_id}/verify", response_model=OutputOut)
def verify_output(
    output_id: uuid.UUID,
    payload: VerifyIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("outputs.verify")),
) -> OutputOut:
    output = get_org_scoped(db, ResearchOutput, output_id, principal)
    db.add(
        Verification(
            organization_id=principal.organization_id,
            output_id=output.id,
            step=payload.step,
            decision=payload.decision,
            note=payload.note,
            verified_by=principal.id,
            decided_at=datetime.now(tz=UTC),
        )
    )
    if payload.decision == "APPROVED":
        output.verification_status = VerificationStatus.VERIFIED
        output.status = OutputStatus.VERIFIED
    else:
        output.verification_status = VerificationStatus.REJECTED
    audit.record(
        db,
        action="output.verify",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="output",
        entity_id=output.id,
        metadata={"step": payload.step, "decision": payload.decision},
    )
    return OutputOut.model_validate(output)


@router.get("/research-outputs/{output_id}/duplicates", response_model=DuplicateOut)
def find_duplicates(
    output_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("outputs.read")),
) -> DuplicateOut:
    output = get_org_scoped(db, ResearchOutput, output_id, principal)
    others = db.scalars(
        select(ResearchOutput).where(
            ResearchOutput.organization_id == principal.organization_id,
            ResearchOutput.id != output.id,
        )
    ).all()
    cands: list[DuplicateCandidate] = []

    def title_sim(a: str, b: str) -> float:
        sa = {w for w in (a or "").lower().split() if len(w) > 2}
        sb = {w for w in (b or "").lower().split() if len(w) > 2}
        return len(sa & sb) / len(sa | sb) if sa and sb else 0.0

    for o in others:
        if output.doi and o.doi and output.doi == o.doi:
            cands.append(
                DuplicateCandidate(
                    output_id=o.id, title=o.title, doi=o.doi, match_type="DOI", score=1.0
                )
            )
        else:
            s = title_sim(output.title, o.title)
            if s > 0.8:
                cands.append(
                    DuplicateCandidate(
                        output_id=o.id,
                        title=o.title,
                        doi=o.doi,
                        match_type="TITLE",
                        score=round(s, 2),
                    )
                )
    return DuplicateOut(candidates=cands)


# ----- Venues -----
@router.get("/publication-venues", response_model=Page[dict])
def list_venues(
    db: Session = Depends(get_db),
    params: PageParams = Depends(page_params),
    principal: Principal = Depends(require("outputs.read")),
) -> Page[dict]:
    stmt = (
        select(PublicationVenue)
        .where(PublicationVenue.organization_id == principal.organization_id)
        .order_by(PublicationVenue.name)
    )
    items, total = paginate(db, stmt, params)
    data = [
        {
            "id": str(v.id),
            "name": v.name,
            "quartile": v.quartile,
            "indexing": v.indexing,
            "issn_print": v.issn_print,
        }
        for v in items
    ]
    return build_page(data, total, params)


@router.post("/publication-venues", status_code=201)
def create_venue(
    payload: VenueIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("outputs.update", "outputs.create")),
) -> dict:
    v = PublicationVenue(organization_id=principal.organization_id, **payload.model_dump())
    db.add(v)
    db.flush()
    return {"ok": True, "venue_id": str(v.id)}
