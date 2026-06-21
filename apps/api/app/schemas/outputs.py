"""Research output schemas."""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel

from app.schemas.common import IdMixin


class AuthorIn(BaseModel):
    author_name: str
    researcher_id: uuid.UUID | None = None
    author_order: int = 1
    corresponding: bool = False
    affiliation: str | None = None
    contribution_role: str | None = None


class OutputCreate(BaseModel):
    output_type: str = "JOURNAL_ARTICLE"
    title: str
    abstract: str | None = None
    venue_name: str | None = None
    venue_id: uuid.UUID | None = None
    publication_date: date | None = None
    year: int | None = None
    doi: str | None = None
    url: str | None = None
    open_access: bool = False
    keywords: list[str] = []
    sdgs: list[str] = []
    project_id: uuid.UUID | None = None
    authors: list[AuthorIn] = []


class OutputUpdate(BaseModel):
    title: str | None = None
    abstract: str | None = None
    venue_name: str | None = None
    publication_date: date | None = None
    year: int | None = None
    doi: str | None = None
    url: str | None = None
    open_access: bool | None = None
    keywords: list[str] | None = None
    visibility: str | None = None
    version: int | None = None


class OutputOut(IdMixin):
    organization_id: uuid.UUID
    output_type: str
    title: str
    abstract: str | None = None
    venue_name: str | None = None
    year: int | None = None
    doi: str | None = None
    url: str | None = None
    open_access: bool
    keywords: list = []
    sdgs: list = []
    project_id: uuid.UUID | None = None
    status: str
    verification_status: str
    visibility: str
    citation_count: int | None = None
    version: int


class VerifyIn(BaseModel):
    step: str = "OFFICE"  # CLAIM|UNIT|LIBRARY|OFFICE
    decision: str = "APPROVED"  # APPROVED|REJECTED
    note: str | None = None


class VenueIn(BaseModel):
    name: str
    issn_print: str | None = None
    issn_online: str | None = None
    publisher: str | None = None
    venue_type: str = "JOURNAL"
    indexing: list[str] = []
    quartile: str | None = None
    ranking_year: int | None = None


class DuplicateCandidate(BaseModel):
    output_id: uuid.UUID
    title: str
    doi: str | None = None
    match_type: str
    score: float


class DuplicateOut(BaseModel):
    candidates: list[DuplicateCandidate]
