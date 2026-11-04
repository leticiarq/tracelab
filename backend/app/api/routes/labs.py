from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.lab import LabStatus
from app.schemas.common import Page
from app.schemas.lab import LabCreate, LabRead, LabUpdate
from app.services import labs as service

router = APIRouter(prefix="/api/labs", tags=["labs"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=LabRead, status_code=status.HTTP_201_CREATED)
async def create_lab(data: LabCreate, db: DbSession) -> object:
    return service.create_lab(db, data)


@router.get("", response_model=Page[LabRead])
async def list_labs(
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    platform_id: Annotated[int | None, Query(ge=1)] = None,
    category_id: Annotated[int | None, Query(ge=1)] = None,
    status_filter: Annotated[LabStatus | None, Query(alias="status")] = None,
) -> object:
    return service.list_labs(
        db, page, page_size, search, platform_id, category_id, status_filter
    )


@router.get("/{lab_id}", response_model=LabRead)
async def get_lab(lab_id: int, db: DbSession) -> object:
    return service.get_lab(db, lab_id)


@router.patch("/{lab_id}", response_model=LabRead)
async def update_lab(lab_id: int, data: LabUpdate, db: DbSession) -> object:
    return service.update_lab(db, lab_id, data)


@router.delete("/{lab_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lab(lab_id: int, db: DbSession) -> Response:
    service.delete_lab(db, lab_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
