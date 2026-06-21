"""Organization, unit, researcher and taxonomy schemas."""

from __future__ import annotations

import uuid

from pydantic import BaseModel

from app.schemas.common import IdMixin


# ---- Units ----
class UnitIn(BaseModel):
    code: str
    name_vi: str
    name_en: str | None = None
    unit_type: str = "FACULTY"
    parent_id: uuid.UUID | None = None
    head_user_id: uuid.UUID | None = None
    coordinator_user_id: uuid.UUID | None = None


class UnitUpdate(BaseModel):
    name_vi: str | None = None
    name_en: str | None = None
    unit_type: str | None = None
    parent_id: uuid.UUID | None = None
    head_user_id: uuid.UUID | None = None
    coordinator_user_id: uuid.UUID | None = None
    is_active: bool | None = None


class UnitOut(IdMixin):
    organization_id: uuid.UUID
    code: str
    name_vi: str
    name_en: str | None = None
    unit_type: str
    parent_id: uuid.UUID | None = None
    head_user_id: uuid.UUID | None = None
    is_active: bool


# ---- Researcher ----
class ResearcherIn(BaseModel):
    user_id: uuid.UUID | None = None
    full_name: str
    publication_name: str | None = None
    academic_title: str | None = None
    degree: str | None = None
    position: str | None = None
    unit_id: uuid.UUID | None = None
    email: str | None = None
    keywords: list[str] = []
    research_methods: list[str] = []
    languages: list[str] = []
    biography_vi: str | None = None
    biography_en: str | None = None
    public_visibility: bool = False


class ResearcherUpdate(BaseModel):
    full_name: str | None = None
    publication_name: str | None = None
    academic_title: str | None = None
    degree: str | None = None
    position: str | None = None
    unit_id: uuid.UUID | None = None
    keywords: list[str] | None = None
    research_methods: list[str] | None = None
    languages: list[str] | None = None
    biography_vi: str | None = None
    biography_en: str | None = None
    public_visibility: bool | None = None


class IdentifierIn(BaseModel):
    type: str
    value: str
    source: str | None = None


class ResearcherOut(IdMixin):
    organization_id: uuid.UUID
    user_id: uuid.UUID | None = None
    full_name: str
    publication_name: str | None = None
    academic_title: str | None = None
    degree: str | None = None
    position: str | None = None
    unit_id: uuid.UUID | None = None
    email: str | None = None
    keywords: list = []
    research_methods: list = []
    languages: list = []
    biography_vi: str | None = None
    biography_en: str | None = None
    public_visibility: bool
    h_index: int | None = None
    citation_count: int | None = None


class TaxonomyOut(IdMixin):
    scheme: str
    code: str
    name_vi: str
    name_en: str | None = None
    level: int
    parent_id: uuid.UUID | None = None


class CVOut(BaseModel):
    profile: ResearcherOut
    identifiers: list[dict]
    outputs: list[dict]
    projects: list[dict]
    generated_at: str
