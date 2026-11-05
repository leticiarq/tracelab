from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.evidence import EvidenceRead
from app.schemas.finding import (
    CVSSAssessmentInput,
    CVSSAssessmentRead,
    FindingCreate,
    FindingDetail,
    FindingRead,
    FindingReorder,
    FindingUpdate,
)
from app.services import findings as service

router = APIRouter(prefix="/api/labs/{lab_id}/findings", tags=["findings"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=FindingRead, status_code=status.HTTP_201_CREATED)
async def create_finding(lab_id: int, data: FindingCreate, db: DbSession) -> object:
    return service.create_finding(db, lab_id, data)


@router.get("", response_model=list[FindingRead])
async def list_findings(lab_id: int, db: DbSession) -> object:
    return service.list_findings(db, lab_id)


@router.patch("/order", response_model=list[FindingRead])
async def reorder_findings(lab_id: int, data: FindingReorder, db: DbSession) -> object:
    return service.reorder_findings(db, lab_id, data)


@router.get("/{finding_id}", response_model=FindingDetail)
async def get_finding(lab_id: int, finding_id: int, db: DbSession) -> object:
    return service.get_finding(db, lab_id, finding_id)


@router.patch("/{finding_id}", response_model=FindingDetail)
async def update_finding(
    lab_id: int, finding_id: int, data: FindingUpdate, db: DbSession
) -> object:
    return service.update_finding(db, lab_id, finding_id, data)


@router.delete("/{finding_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_finding(lab_id: int, finding_id: int, db: DbSession) -> Response:
    service.delete_finding(db, lab_id, finding_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{finding_id}/evidences", response_model=list[EvidenceRead])
async def list_finding_evidences(lab_id: int, finding_id: int, db: DbSession) -> object:
    return service.list_finding_evidences(db, lab_id, finding_id)


@router.put("/{finding_id}/cvss", response_model=CVSSAssessmentRead)
async def save_cvss(
    lab_id: int, finding_id: int, data: CVSSAssessmentInput, db: DbSession
) -> object:
    return service.save_cvss(db, lab_id, finding_id, data)


@router.delete("/{finding_id}/cvss", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cvss(lab_id: int, finding_id: int, db: DbSession) -> Response:
    service.delete_cvss(db, lab_id, finding_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
