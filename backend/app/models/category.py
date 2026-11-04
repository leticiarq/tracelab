from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, nullable=False)
    platform_id: Mapped[int | None] = mapped_column(
        ForeignKey("platforms.id", ondelete="RESTRICT"), index=True
    )

    platform: Mapped["Platform | None"] = relationship(back_populates="categories")  # noqa: F821
    labs: Mapped[list["Lab"]] = relationship(back_populates="category")  # noqa: F821
