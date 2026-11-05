import re
from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.finding import FindingStatus
from app.schemas.evidence import EvidenceRead


class CVSSAssessmentInput(BaseModel):
    version: str = Field(min_length=1, max_length=10)
    vector: str = Field(min_length=1, max_length=255)
    score: float = Field(ge=0, le=10)
    severity: str = Field(min_length=1, max_length=20)
    justification: str = Field(default="", max_length=100_000)

    model_config = ConfigDict(str_strip_whitespace=True)


class CVSSAssessmentRead(CVSSAssessmentInput):
    id: int
    finding_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FindingBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=120)
    cwe_id: str | None = Field(default=None, max_length=20)
    description: str = Field(default="", max_length=100_000)
    technical_details: str = Field(default="", max_length=100_000)
    reproduction_steps: str = Field(default="", max_length=100_000)
    impact: str = Field(default="", max_length=100_000)
    mitigation: str = Field(default="", max_length=100_000)
    status: FindingStatus = FindingStatus.OPEN

    model_config = ConfigDict(str_strip_whitespace=True)

    @field_validator("cwe_id")
    @classmethod
    def validate_cwe(cls, value: str | None) -> str | None:
        if value is None or not value:
            return None
        normalized = value.upper()
        if not re.fullmatch(r"CWE-\d{1,6}", normalized):
            raise ValueError("cwe_id must use the CWE-123 format")
        return normalized


class FindingCreate(FindingBase):
    pass


class FindingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = Field(default=None, max_length=120)
    cwe_id: str | None = Field(default=None, max_length=20)
    description: str | None = Field(default=None, max_length=100_000)
    technical_details: str | None = Field(default=None, max_length=100_000)
    reproduction_steps: str | None = Field(default=None, max_length=100_000)
    impact: str | None = Field(default=None, max_length=100_000)
    mitigation: str | None = Field(default=None, max_length=100_000)
    status: FindingStatus | None = None

    model_config = ConfigDict(str_strip_whitespace=True)
    _validate_cwe = field_validator("cwe_id")(FindingBase.validate_cwe.__func__)

    @model_validator(mode="after")
    def reject_null_required_fields(self) -> Self:
        for field in ("title", "description", "technical_details", "reproduction_steps", "impact", "mitigation", "status"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class FindingRead(FindingBase):
    id: int
    lab_id: int
    slug: str
    display_order: int
    created_at: datetime
    updated_at: datetime
    cvss_assessment: CVSSAssessmentRead | None = None

    model_config = ConfigDict(from_attributes=True)


class FindingDetail(FindingRead):
    evidences: list[EvidenceRead] = Field(default_factory=list)


class FindingReorder(BaseModel):
    finding_ids: list[int] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def reject_duplicates(self) -> Self:
        if len(self.finding_ids) != len(set(self.finding_ids)):
            raise ValueError("finding_ids cannot contain duplicates")
        return self
