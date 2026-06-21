"""Research outputs / publications, authors, identifiers, venues, verification."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import BaseModel
from app.core.enums import OutputStatus, VerificationStatus


class PublicationVenue(BaseModel):
    """Canonical journal/venue registry."""

    __tablename__ = "publication_venues"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    name: Mapped[str] = mapped_column(String(500))
    aliases: Mapped[list] = mapped_column(JSONB, default=list)
    issn_print: Mapped[str | None] = mapped_column(String(20), nullable=True)
    issn_online: Mapped[str | None] = mapped_column(String(20), nullable=True)
    publisher: Mapped[str | None] = mapped_column(String(255), nullable=True)
    venue_type: Mapped[str] = mapped_column(String(30), default="JOURNAL")
    indexing: Mapped[list] = mapped_column(JSONB, default=list)  # [ISI, SCOPUS, ...]
    quartile: Mapped[str | None] = mapped_column(String(5), nullable=True)  # Q1..Q4
    ranking_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")


class ResearchOutput(BaseModel):
    """Master output record (publication, dataset, software, book, patent, etc.)."""

    __tablename__ = "research_outputs"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    output_type: Mapped[str] = mapped_column(String(40), default="JOURNAL_ARTICLE", index=True)
    title: Mapped[str] = mapped_column(String(800))
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    venue_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    venue_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    publication_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    volume: Mapped[str | None] = mapped_column(String(40), nullable=True)
    issue: Mapped[str | None] = mapped_column(String(40), nullable=True)
    pages: Mapped[str | None] = mapped_column(String(40), nullable=True)
    doi: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    url: Mapped[str | None] = mapped_column(String(800), nullable=True)
    open_access: Mapped[bool] = mapped_column(Boolean, default=False)
    license: Mapped[str | None] = mapped_column(String(60), nullable=True)
    keywords: Mapped[list] = mapped_column(JSONB, default=list)
    sdgs: Mapped[list] = mapped_column(JSONB, default=list)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, index=True
    )
    funding_acknowledgement: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=OutputStatus.DRAFT, index=True)
    verification_status: Mapped[str] = mapped_column(
        String(20), default=VerificationStatus.UNVERIFIED
    )
    visibility: Mapped[str] = mapped_column(String(20), default="INTERNAL")
    citation_count: Mapped[int | None] = mapped_column(Integer, nullable=True)


class OutputAuthor(BaseModel):
    __tablename__ = "output_authors"
    __table_args__ = (UniqueConstraint("output_id", "author_order", name="uq_output_author_order"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    output_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("research_outputs.id"), index=True
    )
    researcher_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    author_name: Mapped[str] = mapped_column(String(255))
    author_order: Mapped[int] = mapped_column(Integer, default=1)
    corresponding: Mapped[bool] = mapped_column(Boolean, default=False)
    affiliation: Mapped[str | None] = mapped_column(String(500), nullable=True)
    contribution_role: Mapped[str | None] = mapped_column(String(60), nullable=True)


class OutputIdentifier(BaseModel):
    __tablename__ = "output_identifiers"
    __table_args__ = (UniqueConstraint("type", "value", name="uq_output_identifier"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    output_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("research_outputs.id"), index=True
    )
    type: Mapped[str] = mapped_column(String(20))  # DOI|ISBN|ISSN|HANDLE
    value: Mapped[str] = mapped_column(String(255))
    canonical_url: Mapped[str | None] = mapped_column(String(800), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Verification(BaseModel):
    """Verification action on an output (researcher → unit → library/office)."""

    __tablename__ = "verifications"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    output_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("research_outputs.id"), index=True
    )
    step: Mapped[str] = mapped_column(String(30))  # CLAIM|UNIT|LIBRARY|OFFICE
    decision: Mapped[str] = mapped_column(String(20))  # APPROVED|REJECTED
    verified_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
