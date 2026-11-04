from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReportGenerate(BaseModel):
    confirm_overwrite: bool = False


class ReportSave(BaseModel):
    markdown: str = Field(max_length=1_000_000)


class ReportExport(BaseModel):
    evidence_ids: list[int] = Field(default_factory=list, max_length=100)
    sensitive_reviewed: bool = False


class ReportRead(BaseModel):
    id: int
    lab_id: int
    markdown: str
    revision: int
    generated_at: datetime
    updated_at: datetime
    incomplete_fields: list[str] = Field(default_factory=list)
    sensitive_warnings: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
