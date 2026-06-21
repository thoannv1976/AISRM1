"""Idempotent seed data for local/demo environments."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.enums import (
    CallStatus,
    ProfileRole,
    ProposalStatus,
    SystemRole,
    UnitRole,
    UnitType,
)
from app.core.rbac import BUILTIN_ROLE_PERMISSIONS
from app.core.security import hash_password
from app.models.ai import AIFeature
from app.models.analytics import ReportDefinition
from app.models.funding import FundingCall, FundingProgram, FundingSource
from app.models.identity import Organization, Role, RoleAssignment, User
from app.models.organization import OrganizationUnit
from app.models.outputs import OutputAuthor, ResearchOutput
from app.models.proposals import (
    Deliverable,
    Proposal,
    ProposalBudgetLine,
    ProposalTeamMember,
)
from app.models.researchers import ExpertiseTaxonomy, ResearcherProfile
from app.models.reviews import ReviewerProfile, ReviewTemplate

ORG_CODE = "DEMO"

AI_FEATURES = [
    ("AI-01", "Trích xuất tài liệu", "LOW"),
    ("AI-02", "Tóm tắt hồ sơ", "MEDIUM"),
    ("AI-03", "Kiểm tra tính đầy đủ", "LOW"),
    ("AI-04", "Rà soát nhất quán proposal", "MEDIUM"),
    ("AI-05", "Phân loại lĩnh vực/SDG", "MEDIUM"),
    ("AI-06", "Reviewer matching", "HIGH"),
    ("AI-11", "Trích xuất metadata công bố", "MEDIUM"),
    ("AI-12", "Phát hiện trùng lặp", "MEDIUM"),
    ("AI-15", "Tóm tắt hồ sơ năng lực", "MEDIUM"),
    ("AI-18", "RAG hỏi đáp nội bộ", "MEDIUM"),
    ("AI-19", "Draft báo cáo quản trị", "HIGH"),
    ("AI-20", "Data quality copilot", "LOW"),
]
# code -> the AI feature *code* used by the runner registry
FEATURE_CODE_MAP = {
    "AI-02": "PROPOSAL_SUMMARY",
    "AI-03": "PROPOSAL_COMPLETENESS",
    "AI-04": "PROPOSAL_CONSISTENCY_REVIEW",
    "AI-05": "FIELD_SDG_CLASSIFICATION",
    "AI-06": "REVIEWER_MATCHING",
    "AI-12": "DUPLICATE_DETECTION",
    "AI-15": "RESEARCH_PROFILE_SUMMARY",
}

REPORTS = [
    ("R01", "Danh mục đề xuất theo call", "Proposals"),
    ("R03", "Coverage phản biện", "Review"),
    ("R07", "Danh mục đề tài đang thực hiện", "Projects"),
    ("R11", "Tình hình kinh phí", "Finance"),
    ("R13", "Công bố theo đơn vị/năm", "Outputs"),
    ("R20", "KPI nghiên cứu", "KPI"),
    ("R25", "Báo cáo năm KH&CN", "Annual"),
    ("R28", "Audit report", "Audit"),
]


def _scope_level(code: str) -> str:
    if code in set(SystemRole):
        return "SYSTEM"
    if code in set(UnitRole):
        return "UNIT"
    if code in set(ProfileRole):
        return "PROFILE"
    return "SYSTEM"


def seed_all(demo: bool = True) -> None:
    db: Session = SessionLocal()
    try:
        org = db.scalar(select(Organization).where(Organization.code == ORG_CODE))
        if org is None:
            org = Organization(
                code=ORG_CODE,
                name_vi="Trường Đại học Demo AISRM1",
                name_en="AISRM1 Demo University",
                short_name="AISRM1-U",
            )
            db.add(org)
            db.flush()
            print("[seed] Created organization")

        _seed_roles(db, org.id)
        _seed_features(db, org.id)
        _seed_reports(db, org.id)
        _seed_taxonomy(db, org.id)
        users = _seed_users(db, org.id)
        if demo:
            _seed_demo(db, org.id, users)
        db.commit()
        print("[seed] Done.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _seed_roles(db: Session, org_id: uuid.UUID) -> None:
    for code, perms in BUILTIN_ROLE_PERMISSIONS.items():
        existing = db.scalar(select(Role).where(Role.organization_id == org_id, Role.code == code))
        if existing:
            existing.permissions = perms
            continue
        db.add(
            Role(
                organization_id=org_id,
                code=code,
                name_vi=code,
                name_en=code,
                scope_level=_scope_level(code),
                permissions=perms,
                is_builtin=True,
            )
        )
    db.flush()


def _seed_features(db: Session, org_id: uuid.UUID) -> None:
    for code, name, risk in AI_FEATURES:
        if db.scalar(
            select(AIFeature).where(
                AIFeature.organization_id == org_id,
                AIFeature.code == FEATURE_CODE_MAP.get(code, code),
            )
        ):
            continue
        db.add(
            AIFeature(
                organization_id=org_id,
                code=FEATURE_CODE_MAP.get(code, code),
                name=f"{code} — {name}",
                risk_level=risk,
                enabled=True,
                requires_citations=risk != "LOW",
                allowed_classifications=["PUBLIC", "INTERNAL", "CONFIDENTIAL"],
            )
        )
    db.flush()


def _seed_reports(db: Session, org_id: uuid.UUID) -> None:
    for code, name, cat in REPORTS:
        if db.scalar(
            select(ReportDefinition).where(
                ReportDefinition.organization_id == org_id, ReportDefinition.code == code
            )
        ):
            continue
        db.add(
            ReportDefinition(
                organization_id=org_id,
                code=code,
                name=name,
                category=cat,
                output_formats=["EXCEL", "PDF"],
            )
        )
    db.flush()


def _seed_taxonomy(db: Session, org_id: uuid.UUID) -> None:
    if db.scalar(select(ExpertiseTaxonomy).limit(1)):
        return
    fos = [
        ("1", "Khoa học tự nhiên"),
        ("2", "Kỹ thuật và công nghệ"),
        ("3", "Khoa học y, dược"),
        ("4", "Khoa học nông nghiệp"),
        ("5", "Khoa học xã hội"),
        ("6", "Nhân văn"),
    ]
    for code, name in fos:
        db.add(
            ExpertiseTaxonomy(
                organization_id=org_id, scheme="FOS", code=code, name_vi=name, level=1
            )
        )
    for i in range(1, 18):
        db.add(
            ExpertiseTaxonomy(
                organization_id=org_id, scheme="SDG", code=str(i), name_vi=f"SDG {i}", level=1
            )
        )
    db.flush()


def _seed_units(db: Session, org_id: uuid.UUID) -> dict[str, OrganizationUnit]:
    units: dict[str, OrganizationUnit] = {}
    defs = [
        ("QLKH", "Phòng Quản lý khoa học", UnitType.OFFICE),
        ("TC", "Phòng Tài chính - Kế toán", UnitType.OFFICE),
        ("TV", "Thư viện", UnitType.OFFICE),
        ("CNTT", "Khoa Công nghệ thông tin", UnitType.FACULTY),
        ("KT", "Khoa Kinh tế", UnitType.FACULTY),
        ("MT", "Viện Môi trường", UnitType.INSTITUTE),
    ]
    for code, name, utype in defs:
        u = db.scalar(
            select(OrganizationUnit).where(
                OrganizationUnit.organization_id == org_id, OrganizationUnit.code == code
            )
        )
        if not u:
            u = OrganizationUnit(organization_id=org_id, code=code, name_vi=name, unit_type=utype)
            db.add(u)
            db.flush()
        units[code] = u
    return units


def _get_or_create_user(
    db, org_id, email, name, password, unit_id=None, title=None, external=False
):
    u = db.scalar(select(User).where(User.organization_id == org_id, User.email == email))
    if u:
        return u
    u = User(
        organization_id=org_id,
        email=email,
        display_name=name,
        password_hash=hash_password(password),
        primary_unit_id=unit_id,
        title=title,
        is_external=external,
    )
    db.add(u)
    db.flush()
    return u


def _assign(db, org_id, user_id, role_code, scope_type=None, scope_id=None):
    role = db.scalar(select(Role).where(Role.organization_id == org_id, Role.code == role_code))
    if not role:
        return
    exists = db.scalar(
        select(RoleAssignment).where(
            RoleAssignment.user_id == user_id,
            RoleAssignment.role_id == role.id,
            RoleAssignment.scope_id == scope_id,
        )
    )
    if not exists:
        db.add(
            RoleAssignment(
                organization_id=org_id,
                user_id=user_id,
                role_id=role.id,
                scope_type=scope_type,
                scope_id=scope_id,
            )
        )


def _seed_users(db: Session, org_id: uuid.UUID) -> dict:
    units = _seed_units(db, org_id)
    qlkh = units["QLKH"].id
    cntt = units["CNTT"].id

    admin = _get_or_create_user(
        db, org_id, "admin@aisrm1.edu.vn", "Quản trị hệ thống", "Admin@12345", qlkh, "ThS"
    )
    officer = _get_or_create_user(
        db,
        org_id,
        "officer@aisrm1.edu.vn",
        "Nguyễn Văn Chuyên (QLKH)",
        "Officer@12345",
        qlkh,
        "ThS",
    )
    exec_user = _get_or_create_user(
        db, org_id, "exec@aisrm1.edu.vn", "Trần Thị Lãnh đạo (BGH)", "Exec@12345", qlkh, "PGS.TS"
    )
    pi = _get_or_create_user(
        db, org_id, "pi@aisrm1.edu.vn", "Lê Văn Nghiên (PI)", "Researcher@12345", cntt, "TS"
    )
    reviewer = _get_or_create_user(
        db, org_id, "reviewer@aisrm1.edu.vn", "Phạm Thị Phản biện", "Reviewer@12345", cntt, "PGS.TS"
    )
    coordinator = _get_or_create_user(
        db, org_id, "coordinator@aisrm1.edu.vn", "Hoàng Văn Điều phối", "Coord@12345", cntt, "TS"
    )

    _assign(db, org_id, admin.id, SystemRole.SYSTEM_ADMIN)
    _assign(db, org_id, officer.id, SystemRole.RESEARCH_OFFICE_ADMIN)
    _assign(db, org_id, exec_user.id, SystemRole.EXECUTIVE)
    _assign(db, org_id, pi.id, ProfileRole.PI)
    _assign(db, org_id, reviewer.id, ProfileRole.REVIEWER)
    _assign(db, org_id, coordinator.id, UnitRole.UNIT_RESEARCH_COORDINATOR, "unit", cntt)
    db.flush()

    # Ensure a researcher profile exists for the PI and reviewer
    for u in (pi, reviewer, coordinator):
        if not db.scalar(select(ResearcherProfile).where(ResearcherProfile.user_id == u.id)):
            db.add(
                ResearcherProfile(
                    organization_id=org_id,
                    user_id=u.id,
                    full_name=u.display_name,
                    academic_title=u.title,
                    unit_id=u.primary_unit_id,
                    keywords=["AI", "machine learning"],
                    research_methods=["experimental"],
                    languages=["vi", "en"],
                    public_visibility=True,
                )
            )
    db.flush()
    return {
        "admin": admin,
        "officer": officer,
        "exec": exec_user,
        "pi": pi,
        "reviewer": reviewer,
        "coordinator": coordinator,
        "units": units,
    }


def _seed_demo(db: Session, org_id: uuid.UUID, users: dict) -> None:
    if db.scalar(select(FundingProgram).where(FundingProgram.organization_id == org_id).limit(1)):
        return  # demo content already present

    source = FundingSource(
        organization_id=org_id, code="NSNN", name_vi="Ngân sách nhà nước", source_type="MINISTRY"
    )
    db.add(source)
    db.flush()

    program = FundingProgram(
        organization_id=org_id,
        code="CTR-2026",
        title="Chương trình NCKH cấp trường 2026",
        funder_id=source.id,
        year_from=2026,
        year_to=2026,
        budget_ceiling=5_000_000_000,
        currency="VND",
        objective="Thúc đẩy NCKH",
    )
    db.add(program)
    db.flush()

    now = datetime.now(tz=UTC)
    call = FundingCall(
        organization_id=org_id,
        program_id=program.id,
        code="CALL-2026-01",
        title="Đợt mời nộp đề xuất NCKH cấp trường năm 2026",
        task_level="INSTITUTIONAL",
        open_at=now - timedelta(days=10),
        close_at=now + timedelta(days=30),
        budget_limit=300_000_000,
        currency="VND",
        duration_months=24,
        fields=["1", "2"],
        required_documents=["proposal_form", "cv"],
        status=CallStatus.PUBLISHED,
        published_version=1,
        published_at=now,
    )
    db.add(call)
    db.flush()

    pi = users["pi"]
    pi_profile = db.scalar(select(ResearcherProfile).where(ResearcherProfile.user_id == pi.id))

    # Review template
    db.add(
        ReviewTemplate(
            organization_id=org_id,
            code="RT-STD",
            name="Phiếu đánh giá tiêu chuẩn",
            blind_mode="SINGLE_BLIND",
            criteria=[
                {"code": "SIG", "name": "Tính cấp thiết", "weight": 1, "max_score": 10},
                {"code": "METH", "name": "Phương pháp", "weight": 2, "max_score": 10},
                {"code": "FEAS", "name": "Tính khả thi", "weight": 1, "max_score": 10},
                {"code": "IMPACT", "name": "Tác động", "weight": 1, "max_score": 10},
            ],
        )
    )

    # A draft proposal with team, budget, deliverable
    proposal = Proposal(
        organization_id=org_id,
        call_id=call.id,
        proposal_code="PROP-2026-0001",
        title="Ứng dụng AI trong quản lý nghiên cứu khoa học đại học",
        pi_id=pi.id,
        lead_unit_id=pi.primary_unit_id,
        status=ProposalStatus.DRAFT,
        abstract="Nghiên cứu xây dựng nền tảng AI hỗ trợ quản lý NCKH.",
        content_json={
            "objectives": "Xây dựng nền tảng AISRM.",
            "methods": "Thiết kế hệ thống, thử nghiệm, đánh giá.",
            "impact": "Nâng cao hiệu quả quản lý NCKH.",
        },
        fields=["2"],
        keywords=["AI", "research management"],
        duration_months=24,
        budget_total=0,
        currency="VND",
    )
    db.add(proposal)
    db.flush()
    db.add(
        ProposalTeamMember(
            organization_id=org_id,
            proposal_id=proposal.id,
            researcher_id=pi_profile.id if pi_profile else None,
            role="PI",
            contribution_percent=50,
        )
    )
    db.add(
        Deliverable(
            organization_id=org_id,
            proposal_id=proposal.id,
            code="D1",
            title="Báo cáo tổng kết + phần mềm AISRM1",
            acceptance_criteria="Hệ thống chạy được, có tài liệu.",
        )
    )
    for cat, amt in [("Nhân công", 150_000_000), ("Thiết bị", 80_000_000), ("Khác", 70_000_000)]:
        db.add(
            ProposalBudgetLine(
                organization_id=org_id,
                proposal_id=proposal.id,
                category=cat,
                amount=amt,
                year=2026,
                currency="VND",
            )
        )
    proposal.budget_total = 300_000_000
    db.flush()

    # Reviewer pool
    for name, exp, ext in [
        ("GS. Nguyễn An (ngoài trường)", ["AI", "machine learning"], True),
        ("PGS. Trần Bình", ["software engineering"], False),
        ("TS. Lê Cường", ["data science", "AI"], False),
    ]:
        db.add(
            ReviewerProfile(
                organization_id=org_id,
                full_name=name,
                expertise=exp,
                languages=["vi", "en"],
                is_external=ext,
                is_active=True,
            )
        )

    # Some research outputs
    outputs = [
        (
            "Deep learning for Vietnamese NLP",
            "JOURNAL_ARTICLE",
            2025,
            "10.1234/demo.2025.001",
            "Journal of AI Research",
            "VERIFIED",
        ),
        (
            "A survey on research information systems",
            "JOURNAL_ARTICLE",
            2024,
            "10.1234/demo.2024.014",
            "Scientometrics",
            "UNVERIFIED",
        ),
        ("Bộ dữ liệu công bố khoa học đại học", "DATASET", 2025, None, None, "UNVERIFIED"),
    ]
    for title, otype, year, doi, venue, vstatus in outputs:
        o = ResearchOutput(
            organization_id=org_id,
            output_type=otype,
            title=title,
            year=year,
            doi=doi,
            venue_name=venue,
            status="VERIFIED" if vstatus == "VERIFIED" else "CLAIMED",
            verification_status=vstatus,
            project_id=None,
            visibility="INTERNAL",
        )
        db.add(o)
        db.flush()
        db.add(
            OutputAuthor(
                organization_id=org_id,
                output_id=o.id,
                researcher_id=pi_profile.id if pi_profile else None,
                author_name=pi.display_name,
                author_order=1,
                corresponding=True,
            )
        )
    db.flush()
    print("[seed] Demo content created (program, call, proposal, reviewers, outputs).")
