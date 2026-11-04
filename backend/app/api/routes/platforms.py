from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import Page
from app.schemas.platform import PlatformCreate, PlatformRead, PlatformUpdate
from app.services import platforms as service

router = APIRouter(prefix="/api/platforms", tags=["platforms"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=PlatformRead, status_code=status.HTTP_201_CREATED)
async def create_platform(data: PlatformCreate, db: DbSession) -> object:
    return service.create_platform(db, data)


@router.get("", response_model=Page[PlatformRead])
async def list_platforms(
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> object:
    return service.list_platforms(db, page, page_size)


@router.get("/{platform_id}", response_model=PlatformRead)
async def get_platform(platform_id: int, db: DbSession) -> object:
    return service.get_platform(db, platform_id)


@router.patch("/{platform_id}", response_model=PlatformRead)
async def update_platform(platform_id: int, data: PlatformUpdate, db: DbSession) -> object:
    return service.update_platform(db, platform_id, data)


@router.delete("/{platform_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_platform(platform_id: int, db: DbSession) -> Response:
    service.delete_platform(db, platform_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
