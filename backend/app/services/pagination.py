from math import ceil

from app.schemas.common import Page


def page_result(items: list, total: int, page: int, page_size: int) -> Page:
    return Page(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=ceil(total / page_size) if total else 0,
    )
