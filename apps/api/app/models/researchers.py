"""Researcher profiles, identifiers, expertise taxonomy."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import BaseModel


class ResearcherProfile(BaseModel):
    """360° research profile (1:1 with a user within an organization)."""

    __tablename__ = "researcher_profiles"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", name="uq_profile_org_user"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    full_name: Mapped[str] = mapped_column(String(255))
    publication_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    academic_title: Mapped[str | None] = mapped_column(String(100), nullable=True)  # học hàm
    degree: Mapped[str | None] = mapped_column(String(100), nullable=True)  # học vị
    position: Mapped[str | None] = mapped_column(String(150), nullable=True)
    unit_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    biography_vi: Mapped[str | None] = mapped_column(Text, nullable=True)
    biography_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    keywords: Mapped[list] = mapped_column(JSONB, default=list)
    research_methods: Mapped[list] = mapped_column(JSONB, default=list)
    languages: Mapped[list] = mapped_column(JSONB, default=list)
    public_visibility: Mapped[bool] = mapped_column(Boolean, default=False)
    profile_status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    h_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    citation_count: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ResearcherIdentifier(BaseModel):
    """External identifiers: ORCID / Scopus / WoS / Google Scholar."""

    __tablename__ = "researcher_identifiers"
    __table_args__ = (UniqueConstraint("type", "value", name="uq_identifier_type_value"),)

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    researcher_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("researcher_profiles.id"), index=True
    )
    type: Mapped[str] = mapped_column(String(30))  # ORCID|SCOPUS|WOS|GOOGLE_SCHOLAR
    value: Mapped[str] = mapped_column(String(120))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str | None] = mapped_column(String(60), nullable=True)


class ExpertiseTaxonomy(BaseModel):
    """Hierarchical research-field taxonomy (e.g. OECD FOS) and SDGs."""

    __tablename__ = "expertise_taxonomy"
    __table_args__ = (UniqueConstraint("scheme", "code", name="uq_taxonomy_scheme_code"),)

    organization_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("expertise_taxonomy.id"), nullable=True
    )
    scheme: Mapped[str] = mapped_column(String(30), default="FOS")  # FOS|SDG|INTERNAL
    code: Mapped[str] = mapped_column(String(40))
    name_vi: Mapped[str] = mapped_column(String(255))
    name_en: Mapped[str | None] = mapped_column(String(255), nullable=True)
    level: Mapped[int] = mapped_column(Integer, default=1)


class ResearcherExpertise(BaseModel):
    """Link researcher ↔ expertise; distinguishes AI-suggested vs confirmed."""

    __tablename__ = "researcher_expertise"

    organization_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), index=True)
    researcher_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("researcher_profiles.id"), index=True
    )
    expertise_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("expertise_taxonomy.id")
    )
    proficiency: Mapped[str | None] = mapped_column(String(20), nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="SELF")  # SELF|AI|VERIFIED
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
