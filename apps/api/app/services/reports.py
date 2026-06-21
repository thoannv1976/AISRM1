"""Report engine: data builders, immutable snapshots and file export.

Each builder returns a dict ``{title, columns, rows, summary}`` computed from
authorized data. A report *run* freezes that into an immutable snapshot (with a
hash); exports (Excel/CSV/Word) render the snapshot — never live data.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import Principal
from app.models.identity import AuditLog
from app.models.outputs import ResearchOutput
from app.models.projects import FinanceTransaction, Project
from app.models.proposals import Proposal
from app.models.reviews import Review, ReviewAssignment


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------
def _r01(db, org):  # Danh mục đề xuất theo call
    rows = []
    for p in db.scalars(
        select(Proposal).where(Proposal.organization_id == org).order_by(Proposal.created_at.desc())
    ).all():
        rows.append([p.proposal_code, p.title, p.status, float(p.budget_total or 0)])
    return {
        "title": "R01 — Danh mục đề xuất theo call",
        "columns": ["Mã", "Tên đề tài", "Trạng thái", "Ngân sách"],
        "rows": rows,
        "summary": {"Tổng đề xuất": len(rows)},
    }


def _r03(db, org):  # Coverage phản biện
    rows = []
    for p in db.scalars(select(Proposal).where(Proposal.organization_id == org)).all():
        assigned = (
            db.scalar(
                select(func.count(ReviewAssignment.id)).where(ReviewAssignment.proposal_id == p.id)
            )
            or 0
        )
        submitted = db.scalar(select(func.count(Review.id)).where(Review.proposal_id == p.id)) or 0
        avg = db.scalar(select(func.avg(Review.overall_score)).where(Review.proposal_id == p.id))
        if assigned:
            rows.append(
                [
                    p.proposal_code,
                    p.title,
                    assigned,
                    submitted,
                    round(float(avg), 2) if avg else None,
                ]
            )
    return {
        "title": "R03 — Coverage phản biện",
        "columns": ["Mã", "Đề tài", "Số reviewer", "Đã chấm", "Điểm TB"],
        "rows": rows,
        "summary": {"Số hồ sơ có phản biện": len(rows)},
    }


def _r07(db, org):  # Đề tài đang thực hiện
    rows = []
    for p in db.scalars(select(Project).where(Project.organization_id == org)).all():
        rows.append(
            [
                p.project_code,
                p.title,
                p.status,
                float(p.approved_budget or 0),
                float(p.completion_percent or 0),
            ]
        )
    return {
        "title": "R07 — Danh mục đề tài đang thực hiện",
        "columns": ["Mã", "Tên", "Trạng thái", "Kinh phí", "% hoàn thành"],
        "rows": rows,
        "summary": {"Tổng đề tài": len(rows)},
    }


def _r11(db, org):  # Tình hình kinh phí
    rows = []
    total_b = total_d = 0.0
    for p in db.scalars(select(Project).where(Project.organization_id == org)).all():
        disbursed = (
            db.scalar(
                select(func.coalesce(func.sum(FinanceTransaction.amount), 0)).where(
                    FinanceTransaction.project_id == p.id,
                    FinanceTransaction.transaction_type.in_(["DISBURSED", "ACTUAL"]),
                )
            )
            or 0
        )
        b, d = float(p.approved_budget or 0), float(disbursed)
        total_b += b
        total_d += d
        rows.append([p.project_code, p.title, b, d, b - d])
    return {
        "title": "R11 — Tình hình kinh phí",
        "columns": ["Mã", "Đề tài", "Phê duyệt", "Giải ngân", "Chênh lệch"],
        "rows": rows,
        "summary": {"Tổng phê duyệt": total_b, "Tổng giải ngân": total_d},
    }


def _r13(db, org):  # Công bố theo đơn vị/năm
    rows = []
    for o in db.scalars(
        select(ResearchOutput)
        .where(ResearchOutput.organization_id == org)
        .order_by(ResearchOutput.year.desc().nullslast())
    ).all():
        rows.append(
            [o.title, o.output_type, o.year, o.doi or "", o.venue_name or "", o.verification_status]
        )
    return {
        "title": "R13 — Công bố theo đơn vị/năm",
        "columns": ["Tiêu đề", "Loại", "Năm", "DOI", "Venue", "Xác minh"],
        "rows": rows,
        "summary": {"Tổng công bố": len(rows)},
    }


def _r20(db, org):  # KPI nghiên cứu (đếm công bố đã xác minh theo tác giả)
    from app.models.outputs import OutputAuthor

    rows = []
    res = db.execute(
        select(OutputAuthor.author_name, func.count(ResearchOutput.id))
        .join(ResearchOutput, ResearchOutput.id == OutputAuthor.output_id)
        .where(
            ResearchOutput.organization_id == org,
            ResearchOutput.verification_status == "VERIFIED",
        )
        .group_by(OutputAuthor.author_name)
        .order_by(func.count(ResearchOutput.id).desc())
    ).all()
    for name, cnt in res:
        rows.append([name, int(cnt)])
    return {
        "title": "R20 — KPI nghiên cứu (công bố đã xác minh)",
        "columns": ["Nhà nghiên cứu", "Số công bố verified"],
        "rows": rows,
        "summary": {"Số nhà nghiên cứu có KPI": len(rows)},
    }


def _r22(db, org):  # Chất lượng dữ liệu
    missing_doi = (
        db.scalar(
            select(func.count(ResearchOutput.id)).where(
                ResearchOutput.organization_id == org,
                ResearchOutput.doi.is_(None),
                ResearchOutput.output_type == "JOURNAL_ARTICLE",
            )
        )
        or 0
    )
    unverified = (
        db.scalar(
            select(func.count(ResearchOutput.id)).where(
                ResearchOutput.organization_id == org,
                ResearchOutput.verification_status == "UNVERIFIED",
            )
        )
        or 0
    )
    return {
        "title": "R22 — Báo cáo chất lượng dữ liệu",
        "columns": ["Vấn đề", "Số lượng"],
        "rows": [
            ["Bài báo thiếu DOI", int(missing_doi)],
            ["Công bố chưa xác minh", int(unverified)],
        ],
        "summary": {},
    }


def _r25(db, org):  # Báo cáo năm KH&CN (tổng hợp)
    rows = [
        [
            "Tổng đề xuất",
            db.scalar(select(func.count(Proposal.id)).where(Proposal.organization_id == org)) or 0,
        ],
        [
            "Đề tài",
            db.scalar(select(func.count(Project.id)).where(Project.organization_id == org)) or 0,
        ],
        [
            "Công bố",
            db.scalar(
                select(func.count(ResearchOutput.id)).where(ResearchOutput.organization_id == org)
            )
            or 0,
        ],
    ]
    return {
        "title": "R25 — Báo cáo năm hoạt động KH&CN",
        "columns": ["Chỉ tiêu", "Giá trị"],
        "rows": rows,
        "summary": {},
    }


def _r28(db, org):  # Audit report
    rows = []
    for a in db.scalars(
        select(AuditLog)
        .where(AuditLog.organization_id == org)
        .order_by(AuditLog.occurred_at.desc())
        .limit(500)
    ).all():
        rows.append([a.occurred_at.isoformat(), a.action, a.actor_email or "", a.entity_type or ""])
    return {
        "title": "R28 — Audit report",
        "columns": ["Thời gian", "Hành động", "Người dùng", "Đối tượng"],
        "rows": rows,
        "summary": {"Số sự kiện": len(rows)},
    }


BUILDERS = {
    "R01": _r01,
    "R03": _r03,
    "R07": _r07,
    "R11": _r11,
    "R13": _r13,
    "R20": _r20,
    "R22": _r22,
    "R25": _r25,
    "R28": _r28,
}


def build(code: str, db: Session, org: uuid.UUID) -> dict:
    fn = BUILDERS.get(code)
    if not fn:
        return {
            "title": f"{code} — (chưa hỗ trợ sinh dữ liệu)",
            "columns": [],
            "rows": [],
            "summary": {},
        }
    return fn(db, org)


def snapshot_hash(data: dict) -> str:
    return (
        "sha256:"
        + hashlib.sha256(
            json.dumps(data, sort_keys=True, ensure_ascii=False, default=str).encode()
        ).hexdigest()
    )


# ---------------------------------------------------------------------------
# Exporters
# ---------------------------------------------------------------------------
def to_csv(data: dict) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(data["columns"])
    for row in data["rows"]:
        w.writerow(row)
    return buf.getvalue().encode("utf-8-sig")


def to_xlsx(data: dict) -> bytes:
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data"
    ws.append(data["columns"])
    for row in data["rows"]:
        ws.append(list(row))
    if data.get("summary"):
        ws2 = wb.create_sheet("Summary")
        for k, v in data["summary"].items():
            ws2.append([k, v])
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def to_docx(data: dict, *, narrative: str | None = None, meta: dict | None = None) -> bytes:
    import docx

    doc = docx.Document()
    doc.add_heading(data["title"], level=1)
    if meta:
        for k, v in meta.items():
            doc.add_paragraph(f"{k}: {v}")
    if narrative:
        doc.add_heading("Nhận định", level=2)
        doc.add_paragraph(narrative)
    if data["columns"]:
        table = doc.add_table(rows=1, cols=len(data["columns"]))
        table.style = "Light Grid Accent 1"
        for i, c in enumerate(data["columns"]):
            table.rows[0].cells[i].text = str(c)
        for row in data["rows"]:
            cells = table.add_row().cells
            for i, val in enumerate(row):
                cells[i].text = "" if val is None else str(val)
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


def run_report(db: Session, principal: Principal, code: str, params: dict | None = None):
    from app.models.analytics import ReportRun

    data = build(code, db, principal.organization_id)
    run = ReportRun(
        organization_id=principal.organization_id,
        report_code=code,
        requested_by=principal.id,
        params_json=params or {},
        status="COMPLETED",
        snapshot_json=data,
        snapshot_hash=snapshot_hash(data),
        generated_at=datetime.now(tz=UTC),
    )
    db.add(run)
    db.flush()
    return run
