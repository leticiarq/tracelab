from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FindingStatus(str, Enum):
    OPEN = "open"
    CONFIRMED = "confirmed"
    REMEDIATED = "remediated"
    ACCEPTED_RISK = "accepted_risk"


class Finding(Base):
    __tablename__ = "findings"
    __table_args__ = (UniqueConstraint("lab_id", "slug", name="uq_findings_lab_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    lab_id: Mapped[int] = mapped_column(ForeignKey("labs.id", ondelete="CASCADE"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False)
    category: Mapped[str | None] = mapped_column(String(120))
    cwe_id: Mapped[str | None] = mapped_column(String(20))
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    technical_details: Mapped[str] = mapped_column(Text, default="", nullable=False)
    reproduction_steps: Mapped[str] = mapped_column(Text, default="", nullable=False)
    impact: Mapped[str] = mapped_column(Text, default="", nullable=False)
    mitigation: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[FindingStatus] = mapped_column(
        SqlEnum(FindingStatus, native_enum=False, values_callable=lambda values: [item.value for item in values]),
        default=FindingStatus.OPEN,
        index=True,
        nullable=False,
    )
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    lab: Mapped["Lab"] = relationship(back_populates="findings")  # noqa: F821
    evidences: Mapped[list["Evidence"]] = relationship(back_populates="finding")  # noqa: F821
    cvss_assessment: Mapped["CVSSAssessment | None"] = relationship(  # noqa: F821
        back_populates="finding", cascade="all, delete-orphan", passive_deletes=True, uselist=False
    )


class CVSSAssessment(Base):
    __tablename__ = "cvss_assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    finding_id: Mapped[int] = mapped_column(
        ForeignKey("findings.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )
    version: Mapped[str] = mapped_column(String(10), nullable=False)
    vector: Mapped[str] = mapped_column(String(255), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    justification: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    finding: Mapped[Finding] = relationship(back_populates="cvss_assessment")
