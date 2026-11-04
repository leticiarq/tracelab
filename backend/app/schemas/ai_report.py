from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.ai_report_version import (
    AIReportAction,
    AIReportStatus,
    AIReportStyle,
)


class AIReportGenerate(BaseModel):
    action: AIReportAction
    style: AIReportStyle = AIReportStyle.PROFESSIONAL
    evidence_ids: list[int] = Field(default_factory=list, max_length=100)


class AIReportResult(BaseModel):
    suggestion: str = Field(min_length=1, max_length=1_000_000)
    ambiguities: list[str] = Field(default_factory=list, max_length=30)
    questions: list[str] = Field(default_factory=list, max_length=30)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AIReportReview(BaseModel):
    action: str = Field(pattern="^(accept|reject)$")


class AIReportVersionRead(BaseModel):
    id: int
    lab_id: int
    action: AIReportAction
    style: AIReportStyle
    status: AIReportStatus
    model_name: str
    original_text: str
    suggested_text: str
    ambiguities: list[str]
    questions: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
