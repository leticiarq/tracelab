from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.lab import Lab
from app.models.platform import Platform
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.schemas.common import Page
from app.services.errors import ConflictError, NotFoundError
from app.services.pagination import page_result
from app.services.slug import unique_slug


def _ensure_platform(db: Session, platform_id: int | None) -> None:
    if platform_id is not None and db.get(Platform, platform_id) is None:
        raise NotFoundError("Platform not found")


def list_categories(db: Session, page: int, page_size: int, platform_id: int | None) -> Page:
    filters = []
    if platform_id is not None:
        filters.append(Category.platform_id == platform_id)
    total = db.scalar(select(func.count()).select_from(Category).where(*filters)) or 0
    items = list(
        db.scalars(
            select(Category)
            .where(*filters)
            .order_by(Category.name, Category.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return page_result(items, total, page, page_size)


def get_category(db: Session, category_id: int) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise NotFoundError("Category not found")
    return category


def create_category(db: Session, data: CategoryCreate) -> Category:
    _ensure_platform(db, data.platform_id)
    category = Category(
        name=data.name,
        platform_id=data.platform_id,
        slug=unique_slug(db, Category, data.name, fallback="category"),
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(db: Session, category_id: int, data: CategoryUpdate) -> Category:
    category = get_category(db, category_id)
    changes = data.model_dump(exclude_unset=True)
    if "platform_id" in changes:
        new_platform_id = changes["platform_id"]
        _ensure_platform(db, new_platform_id)
        if new_platform_id is not None:
            mismatched_lab = db.scalar(
                select(Lab.id)
                .where(Lab.category_id == category_id, Lab.platform_id != new_platform_id)
                .limit(1)
            )
            if mismatched_lab is not None:
                raise ConflictError("Category platform conflicts with existing labs")
        category.platform_id = new_platform_id
    if "name" in changes:
        category.name = changes["name"]
        category.slug = unique_slug(
            db, Category, changes["name"], exclude_id=category.id, fallback="category"
        )
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category_id: int) -> None:
    category = get_category(db, category_id)
    if db.scalar(select(Lab.id).where(Lab.category_id == category_id).limit(1)) is not None:
        raise ConflictError("Category is still referenced by labs")
    db.delete(category)
    db.commit()
