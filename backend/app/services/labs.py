from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.lab import Lab, LabStatus
from app.models.platform import Platform
from app.schemas.common import Page
from app.schemas.lab import LabCreate, LabUpdate
from app.services.errors import InvalidRelationError, NotFoundError
from app.services.pagination import page_result
from app.services.slug import unique_slug


def _ensure_relations(db: Session, platform_id: int, category_id: int | None) -> None:
    if db.get(Platform, platform_id) is None:
        raise NotFoundError("Platform not found")
    if category_id is None:
        return
    category = db.get(Category, category_id)
    if category is None:
        raise NotFoundError("Category not found")
    if category.platform_id is not None and category.platform_id != platform_id:
        raise InvalidRelationError("Category does not belong to the selected platform")


def list_labs(
    db: Session,
    page: int,
    page_size: int,
    search: str | None,
    platform_id: int | None,
    category_id: int | None,
    status: LabStatus | None,
) -> Page:
    filters = []
    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        filters.append(Lab.title.ilike(f"%{escaped}%", escape="\\"))
    if platform_id is not None:
        filters.append(Lab.platform_id == platform_id)
    if category_id is not None:
        filters.append(Lab.category_id == category_id)
    if status is not None:
        filters.append(Lab.status == status)
    total = db.scalar(select(func.count()).select_from(Lab).where(*filters)) or 0
    items = list(
        db.scalars(
            select(Lab)
            .where(*filters)
            .order_by(Lab.created_at.desc(), Lab.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    )
    return page_result(items, total, page, page_size)


def get_lab(db: Session, lab_id: int) -> Lab:
    lab = db.get(Lab, lab_id)
    if lab is None:
        raise NotFoundError("Lab not found")
    return lab


def create_lab(db: Session, data: LabCreate) -> Lab:
    _ensure_relations(db, data.platform_id, data.category_id)
    values = data.model_dump()
    lab = Lab(**values, slug=unique_slug(db, Lab, data.title, fallback="lab"))
    if lab.status == LabStatus.SOLVED:
        lab.solved_at = datetime.now(timezone.utc)
    db.add(lab)
    db.commit()
    db.refresh(lab)
    return lab


def update_lab(db: Session, lab_id: int, data: LabUpdate) -> Lab:
    lab = get_lab(db, lab_id)
    changes = data.model_dump(exclude_unset=True)
    platform_id = changes.get("platform_id", lab.platform_id)
    category_id = changes.get("category_id", lab.category_id)
    _ensure_relations(db, platform_id, category_id)

    if "title" in changes:
        lab.slug = unique_slug(db, Lab, changes["title"], exclude_id=lab.id, fallback="lab")
    for field, value in changes.items():
        setattr(lab, field, value)
    if "status" in changes:
        if changes["status"] == LabStatus.SOLVED and lab.solved_at is None:
            lab.solved_at = datetime.now(timezone.utc)
        elif changes["status"] != LabStatus.SOLVED:
            lab.solved_at = None
    lab.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(lab)
    return lab


def delete_lab(db: Session, lab_id: int) -> None:
    lab = get_lab(db, lab_id)
    db.delete(lab)
    db.commit()
