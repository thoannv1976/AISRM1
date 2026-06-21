"""Report catalog, runs (immutable snapshots) and file export."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api._helpers import get_org_scoped
from app.core.db import get_db
from app.core.deps import Principal, require
from app.core.errors import ValidationFailed
from app.models.analytics import ReportDefinition, ReportRun
from app.services import audit, reports

router = APIRouter()


@router.get("")
def list_reports(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("reports.read")),
) -> list[dict]:
    defs = db.scalars(
        select(ReportDefinition)
        .where(ReportDefinition.organization_id == principal.organization_id)
        .order_by(ReportDefinition.code)
    ).all()
    return [
        {
            "code": d.code,
            "name": d.name,
            "category": d.category,
            "supported": d.code in reports.BUILDERS,
            "output_formats": d.output_formats or ["EXCEL", "CSV", "WORD"],
        }
        for d in defs
    ]


@router.post("/{code}/runs", status_code=201)
def create_run(
    code: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("reports.read")),
) -> dict:
    run = reports.run_report(db, principal, code.upper())
    audit.record(
        db,
        action="report.run",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="report_run",
        entity_id=run.id,
        metadata={"code": code.upper()},
    )
    return {
        "id": str(run.id),
        "report_code": run.report_code,
        "status": run.status,
        "snapshot": run.snapshot_json,
        "snapshot_hash": run.snapshot_hash,
        "generated_at": run.generated_at.isoformat() if run.generated_at else None,
    }


@router.get("/runs/{run_id}")
def get_run(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("reports.read")),
) -> dict:
    run = get_org_scoped(db, ReportRun, run_id, principal)
    return {
        "id": str(run.id),
        "report_code": run.report_code,
        "status": run.status,
        "snapshot": run.snapshot_json,
        "snapshot_hash": run.snapshot_hash,
        "generated_at": run.generated_at.isoformat() if run.generated_at else None,
    }


@router.get("/runs/{run_id}/export")
def export_run(
    run_id: uuid.UUID,
    format: str = "xlsx",
    db: Session = Depends(get_db),
    principal: Principal = Depends(require("reports.export", "reports.read")),
) -> Response:
    run = get_org_scoped(db, ReportRun, run_id, principal)
    data = run.snapshot_json or {"title": run.report_code, "columns": [], "rows": [], "summary": {}}
    fmt = format.lower()
    meta = {
        "Mã báo cáo": run.report_code,
        "Tạo lúc": run.generated_at.isoformat() if run.generated_at else "",
        "Snapshot": run.snapshot_hash,
    }
    audit.record(
        db,
        action="report.export",
        actor_id=principal.id,
        organization_id=principal.organization_id,
        entity_type="report_run",
        entity_id=run.id,
        metadata={"format": fmt},
    )
    if fmt == "csv":
        return _file(reports.to_csv(data), "text/csv", f"{run.report_code}.csv")
    if fmt in {"xlsx", "excel"}:
        return _file(
            reports.to_xlsx(data),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            f"{run.report_code}.xlsx",
        )
    if fmt in {"docx", "word"}:
        return _file(
            reports.to_docx(data, meta=meta),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            f"{run.report_code}.docx",
        )
    raise ValidationFailed("Định dạng không hỗ trợ (csv|xlsx|docx).")


def _file(content: bytes, media_type: str, filename: str) -> Response:
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
