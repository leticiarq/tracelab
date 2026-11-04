from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.schemas.common import Page
from app.services import categories as service

router = APIRouter(prefix="/api/categories", tags=["categories"])
DbSession = Annotated[Session, Depends(get_db)]


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(data: CategoryCreate, db: DbSession) -> object:
    return service.create_category(db, data)


@router.get("", response_model=Page[CategoryRead])
async def list_categories(
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    platform_id: Annotated[int | None, Query(ge=1)] = None,
) -> object:
    return service.list_categories(db, page, page_size, platform_id)


@router.get("/{category_id}", response_model=CategoryRead)
async def get_category(category_id: int, db: DbSession) -> object:
    return service.get_category(db, category_id)


@router.patch("/{category_id}", response_model=CategoryRead)
async def update_category(category_id: int, data: CategoryUpdate, db: DbSession) -> object:
    return service.update_category(db, category_id, data)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(category_id: int, db: DbSession) -> Response:
    service.delete_category(db, category_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
