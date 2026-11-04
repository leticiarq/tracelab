from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.routes import ai as ai_routes
from app.db.session import get_db
from app.schemas.evidence import EvidenceRead, EvidenceReorder, EvidenceUpdate
from app.schemas.smart_evidence import SmartEvidenceRead, SmartEvidenceReview
from app.services import evidences as service
from app.services import smart_evidence

router = APIRouter(prefix="/api/labs/{lab_id}/evidences", tags=["evidences"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[EvidenceRead])
async def list_evidences(lab_id: int, db: DbSession) -> object:
    return service.list_evidences(db, lab_id)


@router.post("", response_model=list[EvidenceRead], status_code=status.HTTP_201_CREATED)
async def upload_evidences(
    lab_id: int,
    db: DbSession,
    files: Annotated[list[UploadFile], File(description="Evidence files")],
) -> object:
    return await service.upload_evidences(db, lab_id, files)


@router.get("/{evidence_id}/analysis", response_model=SmartEvidenceRead | None)
async def get_smart_analysis(
    lab_id: int, evidence_id: int, db: DbSession
) -> SmartEvidenceRead | None:
    analysis = smart_evidence.get_analysis(db, lab_id, evidence_id)
    return SmartEvidenceRead.model_validate(analysis) if analysis else None


@router.post("/{evidence_id}/analysis", response_model=SmartEvidenceRead)
async def analyze_evidence(
    lab_id: int, evidence_id: int, db: DbSession, force: bool = False
) -> SmartEvidenceRead:
    analysis, cached = await smart_evidence.analyze(
        db, lab_id, evidence_id, ai_routes.get_ai_service(), force=force
    )
    response = SmartEvidenceRead.model_validate(analysis)
    return response.model_copy(update={"cached": cached})


@router.patch("/{evidence_id}/analysis", response_model=SmartEvidenceRead)
async def review_smart_analysis(
    lab_id: int,
    evidence_id: int,
    data: SmartEvidenceReview,
    db: DbSession,
) -> SmartEvidenceRead:
    return SmartEvidenceRead.model_validate(
        smart_evidence.review(db, lab_id, evidence_id, data)
    )


@router.patch("/order", response_model=list[EvidenceRead])
async def reorder_evidences(lab_id: int, data: EvidenceReorder, db: DbSession) -> object:
    return service.reorder_evidences(db, lab_id, data)


@router.patch("/{evidence_id}", response_model=EvidenceRead)
async def update_evidence(
    lab_id: int, evidence_id: int, data: EvidenceUpdate, db: DbSession
) -> object:
    return service.update_evidence(db, lab_id, evidence_id, data)


def _file_response(lab_id: int, evidence_id: int, db: Session, download: bool) -> Response:
    evidence = service.get_evidence(db, lab_id, evidence_id)
    path = service.evidence_path(evidence)
    media_type = evidence.mime_type if evidence.mime_type.startswith("image/") else "text/plain"
    headers = {
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "private, no-store",
        "Content-Security-Policy": "default-src 'none'; sandbox",
        "Content-Disposition": (
            f"attachment; filename*=UTF-8''{quote(evidence.original_filename)}"
            if download
            else "inline"
        ),
    }
    return Response(content=path.read_bytes(), media_type=media_type, headers=headers)


@router.get("/{evidence_id}/content")
async def view_evidence(lab_id: int, evidence_id: int, db: DbSession) -> Response:
    return _file_response(lab_id, evidence_id, db, False)


@router.get("/{evidence_id}/download")
async def download_evidence(lab_id: int, evidence_id: int, db: DbSession) -> Response:
    return _file_response(lab_id, evidence_id, db, True)


@router.delete("/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_evidence(lab_id: int, evidence_id: int, db: DbSession) -> Response:
    service.delete_evidence(db, lab_id, evidence_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
