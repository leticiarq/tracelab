from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LabStatus(str, Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    SOLVED = "solved"
    DOCUMENTED = "documented"


class Lab(Base):
    __tablename__ = "labs"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), unique=True, nullable=False)
    platform_id: Mapped[int] = mapped_column(
        ForeignKey("platforms.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT"), index=True
    )
    source_url: Mapped[str | None] = mapped_column(String(2048))
    difficulty: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[LabStatus] = mapped_column(
        SqlEnum(LabStatus, native_enum=False, values_callable=lambda values: [item.value for item in values]),
        default=LabStatus.TODO,
        index=True,
        nullable=False,
    )
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    objective: Mapped[str | None] = mapped_column(Text)
    vulnerability_description: Mapped[str | None] = mapped_column(Text)
    impact: Mapped[str | None] = mapped_column(Text)
    mitigation: Mapped[str | None] = mapped_column(Text)
    learnings: Mapped[str | None] = mapped_column(Text)
    resolution_steps: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    solved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    platform: Mapped["Platform"] = relationship(back_populates="labs")  # noqa: F821
    category: Mapped["Category | None"] = relationship(back_populates="labs")  # noqa: F821
    evidences: Mapped[list["Evidence"]] = relationship(  # noqa: F821
        back_populates="lab", cascade="all, delete-orphan", passive_deletes=True
    )
    findings: Mapped[list["Finding"]] = relationship(  # noqa: F821
        back_populates="lab", cascade="all, delete-orphan", passive_deletes=True,
        order_by="Finding.display_order",
    )
    report: Mapped["Report | None"] = relationship(  # noqa: F821
        back_populates="lab", cascade="all, delete-orphan", passive_deletes=True
    )
