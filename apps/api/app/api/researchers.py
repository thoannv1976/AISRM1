"""Researcher profiles, identifiers, expertise, CV."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api._helpers import apply_updates, get_org_scoped
from app.core.db import get_db
from app.core.deps import Principal, require
from app.core.pagination import Page, PageParams, build_page, page_params, paginate
from app.models.outputs import OutputAuthor, ResearchOutput
from app.models.researchers import (
    ExpertiseTaxonomy,
    ResearcherIdentifier,
    ResearcherProfile,
)
from app.schemas.core import (
    CVOut,
    IdentifierIn,
    ResearcherIn,
    ResearcherOut,
    ResearcherUpdate,
    TaxonomyOut,
)
from app.services import audit

router = APIRouter()


@router.get("", response_model=Page[ResearcherOut])
def list_researchers(
    q: str | None = None,
    unit_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    params: PageParams = Depends(page_params),
    principal: Principal = Depends(require("researchers.read")),
) -> Page[ResearcherOut]:
    stmt = select(ResearcherProfile).where(
        ResearcherProfile.organization_id == principal.organization_id
    )
    if q:
        stmt = stmt.where(ResearcherProfile.full_name.ilike(f"%{q}%"))
    if unit_id:
        stmt = stmt.where(ResearcherProfile.unit_id == unit_id)
    stmt = stmt.order_by(ResearcherProfile.full_name)
    items, total = paginate(db, stmt, params)
    return build_page([ResearcherOut.model_validate(i) for i in items], total, params)


@router.post("", response_model=ResearcherOut, status_code=201)
def create_researcher(
    payload: ResearcherIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("researchers.create")),
) -> ResearcherOut:
    prof = ResearcherProfile(
        organization_id=principal.organization_id, created_by=principal.id, **payload.model_dump()
    )
    db.add(prof)
    db.flush()
    audit.record(
        db,
        action="researcher.create",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="researcher",
        entity_id=prof.id,
    )
    return ResearcherOut.model_validate(prof)


@router.get("/expertise-taxonomy", response_model=list[TaxonomyOut])
def list_taxonomy(
    scheme: str | None = None,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("researchers.read")),
) -> list[TaxonomyOut]:
    stmt = select(ExpertiseTaxonomy).order_by(ExpertiseTaxonomy.scheme, ExpertiseTaxonomy.code)
    if scheme:
        stmt = stmt.where(ExpertiseTaxonomy.scheme == scheme)
    return [TaxonomyOut.model_validate(t) for t in db.scalars(stmt).all()]


@router.get("/{researcher_id}", response_model=ResearcherOut)
def get_researcher(
    researcher_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("researchers.read")),
) -> ResearcherOut:
    return ResearcherOut.model_validate(
        get_org_scoped(db, ResearcherProfile, researcher_id, principal)
    )


@router.patch("/{researcher_id}", response_model=ResearcherOut)
def update_researcher(
    researcher_id: uuid.UUID,
    payload: ResearcherUpdate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("researchers.update")),
) -> ResearcherOut:
    prof = get_org_scoped(db, ResearcherProfile, researcher_id, principal)
    apply_updates(prof, payload.model_dump(exclude_unset=True))
    audit.record(
        db,
        action="researcher.update",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="researcher",
        entity_id=prof.id,
    )
    return ResearcherOut.model_validate(prof)


@router.post("/{researcher_id}/identifiers", status_code=201)
def add_identifier(
    researcher_id: uuid.UUID,
    payload: IdentifierIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("researchers.update")),
) -> dict:
    prof = get_org_scoped(db, ResearcherProfile, researcher_id, principal)
    ident = ResearcherIdentifier(
        organization_id=principal.organization_id,
        researcher_id=prof.id,
        type=payload.type.upper(),
        value=payload.value,
        source=payload.source,
    )
    db.add(ident)
    audit.record(
        db,
        action="researcher.identifier.add",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="researcher",
        entity_id=prof.id,
    )
    return {"ok": True}


@router.get("/{researcher_id}/cv", response_model=CVOut)
def get_cv(
    researcher_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("researchers.read")),
) -> CVOut:
    prof = get_org_scoped(db, ResearcherProfile, researcher_id, principal)
    idents = db.scalars(
        select(ResearcherIdentifier).where(ResearcherIdentifier.researcher_id == prof.id)
    ).all()
    output_rows = (
        db.execute(
            select(ResearchOutput)
            .join(OutputAuthor, OutputAuthor.output_id == ResearchOutput.id)
            .where(OutputAuthor.researcher_id == prof.id)
            .order_by(ResearchOutput.year.desc())
        )
        .scalars()
        .all()
    )
    return CVOut(
        profile=ResearcherOut.model_validate(prof),
        identifiers=[
            {"type": i.type, "value": i.value, "verified": bool(i.verified_at)} for i in idents
        ],
        outputs=[
            {"title": o.title, "year": o.year, "venue": o.venue_name, "doi": o.doi}
            for o in output_rows
        ],
        projects=[],
        generated_at=datetime.now(tz=UTC).isoformat(),
    )
