from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.report import ReportExport, ReportGenerate, ReportRead, ReportSave
from app.services import reports as service

router = APIRouter(prefix="/api/labs/{lab_id}/report", tags=["reports"])
DbSession = Annotated[Session, Depends(get_db)]


def _read(db: Session, lab_id: int, report: object) -> dict[str, object]:
    lab = service._lab(db, lab_id)
    evidences = service._evidences(db, lab_id)
    findings = service._findings(db, lab_id)
    return {
        "id": report.id,
        "lab_id": report.lab_id,
        "markdown": report.markdown,
        "revision": report.revision,
        "generated_at": report.generated_at,
        "updated_at": report.updated_at,
        "incomplete_fields": service.incomplete_fields(lab, findings, evidences),
        "sensitive_warnings": service.sensitive_warnings(report.markdown),
    }


@router.get("", response_model=ReportRead | None)
async def get_report(lab_id: int, db: DbSession) -> object:
    report = service.get_report(db, lab_id)
    return None if report is None else _read(db, lab_id, report)


@router.post("/generate", response_model=ReportRead)
async def generate_report(lab_id: int, data: ReportGenerate, db: DbSession) -> object:
    return _read(db, lab_id, service.generate_report(db, lab_id, data.confirm_overwrite))


@router.put("", response_model=ReportRead)
async def save_report(lab_id: int, data: ReportSave, db: DbSession) -> object:
    return _read(db, lab_id, service.save_report(db, lab_id, data.markdown))


@router.post("/export")
async def export_report(lab_id: int, data: ReportExport, db: DbSession) -> Response:
    content, filename = service.export_report(
        db, lab_id, data.evidence_ids, data.sensitive_reviewed
    )
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
