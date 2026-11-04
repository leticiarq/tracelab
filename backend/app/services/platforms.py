from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.lab import Lab
from app.models.platform import Platform
from app.schemas.common import Page
from app.schemas.platform import PlatformCreate, PlatformUpdate
from app.services.errors import ConflictError, NotFoundError
from app.services.pagination import page_result
from app.services.slug import unique_slug


def list_platforms(db: Session, page: int, page_size: int) -> Page:
    total = db.scalar(select(func.count()).select_from(Platform)) or 0
    items = list(
        db.scalars(
            select(Platform).order_by(Platform.name, Platform.id).offset((page - 1) * page_size).limit(page_size)
        )
    )
    return page_result(items, total, page, page_size)


def get_platform(db: Session, platform_id: int) -> Platform:
    platform = db.get(Platform, platform_id)
    if platform is None:
        raise NotFoundError("Platform not found")
    return platform


def create_platform(db: Session, data: PlatformCreate) -> Platform:
    platform = Platform(
        name=data.name,
        website_url=data.website_url,
        slug=unique_slug(db, Platform, data.name, fallback="platform"),
    )
    db.add(platform)
    db.commit()
    db.refresh(platform)
    return platform


def update_platform(db: Session, platform_id: int, data: PlatformUpdate) -> Platform:
    platform = get_platform(db, platform_id)
    changes = data.model_dump(exclude_unset=True)
    if "name" in changes:
        platform.name = changes["name"]
        platform.slug = unique_slug(
            db, Platform, changes["name"], exclude_id=platform.id, fallback="platform"
        )
    if "website_url" in changes:
        platform.website_url = changes["website_url"]
    db.commit()
    db.refresh(platform)
    return platform


def delete_platform(db: Session, platform_id: int) -> None:
    platform = get_platform(db, platform_id)
    has_categories = db.scalar(select(Category.id).where(Category.platform_id == platform_id).limit(1))
    has_labs = db.scalar(select(Lab.id).where(Lab.platform_id == platform_id).limit(1))
    if has_categories is not None or has_labs is not None:
        raise ConflictError("Platform is still referenced by categories or labs")
    db.delete(platform)
    db.commit()
