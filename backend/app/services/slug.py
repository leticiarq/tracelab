import re
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session


def slugify(value: str, fallback: str = "item") -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug or fallback


def unique_slug(
    db: Session,
    model: type,
    value: str,
    *,
    exclude_id: int | None = None,
    fallback: str = "item",
) -> str:
    base = slugify(value, fallback=fallback)
    candidate = base
    suffix = 2
    while True:
        statement = select(model.id).where(model.slug == candidate)
        if exclude_id is not None:
            statement = statement.where(model.id != exclude_id)
        if db.scalar(statement) is None:
            return candidate
        candidate = f"{base}-{suffix}"
        suffix += 1
