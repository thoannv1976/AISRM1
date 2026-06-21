"""Organization units."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api._helpers import apply_updates, get_org_scoped
from app.core.db import get_db
from app.core.deps import Principal, require
from app.core.pagination import Page, PageParams, build_page, page_params, paginate
from app.models.organization import OrganizationUnit
from app.schemas.core import UnitIn, UnitOut, UnitUpdate
from app.services import audit

router = APIRouter()


@router.get("", response_model=Page[UnitOut])
def list_units(
    db: Session = Depends(get_db),
    params: PageParams = Depends(page_params),
    principal: Principal = Depends(require("units.read")),
) -> Page[UnitOut]:
    stmt = (
        select(OrganizationUnit)
        .where(OrganizationUnit.organization_id == principal.organization_id)
        .order_by(OrganizationUnit.code)
    )
    items, total = paginate(db, stmt, params)
    return build_page([UnitOut.model_validate(i) for i in items], total, params)


@router.post("", response_model=UnitOut, status_code=201)
def create_unit(
    payload: UnitIn,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("units.create")),
) -> UnitOut:
    unit = OrganizationUnit(
        organization_id=principal.organization_id,
        created_by=principal.id,
        **payload.model_dump(),
    )
    db.add(unit)
    db.flush()
    audit.record(
        db,
        action="unit.create",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="unit",
        entity_id=unit.id,
    )
    return UnitOut.model_validate(unit)


@router.get("/{unit_id}", response_model=UnitOut)
def get_unit(
    unit_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("units.read")),
) -> UnitOut:
    return UnitOut.model_validate(get_org_scoped(db, OrganizationUnit, unit_id, principal))


@router.patch("/{unit_id}", response_model=UnitOut)
def update_unit(
    unit_id: uuid.UUID,
    payload: UnitUpdate,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("units.update")),
) -> UnitOut:
    unit = get_org_scoped(db, OrganizationUnit, unit_id, principal)
    apply_updates(unit, payload.model_dump(exclude_unset=True))
    audit.record(
        db,
        action="unit.update",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="unit",
        entity_id=unit.id,
    )
    return UnitOut.model_validate(unit)
