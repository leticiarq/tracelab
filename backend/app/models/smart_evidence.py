from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SmartEvidenceStatus(str, Enum):
    SUGGESTED = "suggested"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class SmartEvidenceAnalysis(Base):
    __tablename__ = "smart_evidence_analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    evidence_id: Mapped[int] = mapped_column(
        ForeignKey("evidences.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    image_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str] = mapped_column(String(200), nullable=False)
    instruction_version: Mapped[str] = mapped_column(String(40), nullable=False)
    context_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    detected_tool: Mapped[str | None] = mapped_column(String(200))
    visible_observations: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    objective_explanation: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_step: Mapped[str | None] = mapped_column(String(200))
    suggested_caption: Mapped[str] = mapped_column(Text, nullable=False)
    possible_sensitive_data: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    uncertainties: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    status: Mapped[SmartEvidenceStatus] = mapped_column(
        SqlEnum(
            SmartEvidenceStatus,
            native_enum=False,
            values_callable=lambda values: [item.value for item in values],
        ),
        default=SmartEvidenceStatus.SUGGESTED,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    evidence: Mapped["Evidence"] = relationship(back_populates="smart_analysis")  # noqa: F821
