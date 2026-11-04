from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class AIReportAction(str, Enum):
    IMPROVE_NOTES = "improve_notes"
    EXPLAIN_VULNERABILITY = "explain_vulnerability"
    MISSING_INFORMATION = "missing_information"
    GENERATE_README = "generate_readme"


class AIReportStyle(str, Enum):
    PROFESSIONAL = "professional"
    GITHUB = "github"
    STUDY = "study"


class AIReportStatus(str, Enum):
    SUGGESTED = "suggested"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class AIReportVersion(Base):
    __tablename__ = "ai_report_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    lab_id: Mapped[int] = mapped_column(
        ForeignKey("labs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    action: Mapped[AIReportAction] = mapped_column(
        SqlEnum(AIReportAction, native_enum=False, values_callable=lambda values: [v.value for v in values]),
        nullable=False,
    )
    style: Mapped[AIReportStyle] = mapped_column(
        SqlEnum(AIReportStyle, native_enum=False, values_callable=lambda values: [v.value for v in values]),
        nullable=False,
    )
    status: Mapped[AIReportStatus] = mapped_column(
        SqlEnum(AIReportStatus, native_enum=False, values_callable=lambda values: [v.value for v in values]),
        default=AIReportStatus.SUGGESTED,
        nullable=False,
    )
    model_name: Mapped[str] = mapped_column(String(200), nullable=False)
    original_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    suggested_text: Mapped[str] = mapped_column(Text, nullable=False)
    ambiguities: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    questions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    lab: Mapped["Lab"] = relationship()  # noqa: F821
