from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.evidence import EvidenceRead, EvidenceReorder, EvidenceUpdate
from app.services import evidences as service

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
