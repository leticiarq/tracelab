from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvidenceRead(BaseModel):
    id: int
    lab_id: int
    finding_id: int | None
    original_filename: str
    stored_filename: str
    mime_type: str
    file_size: int
    sha256: str
    description: str
    step_label: str | None
    display_order: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EvidenceUpdate(BaseModel):
    description: str | None = Field(default=None, max_length=2_000)
    step_label: str | None = Field(default=None, max_length=200)
    finding_id: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def reject_null_description(self) -> "EvidenceUpdate":
        if "description" in self.model_fields_set and self.description is None:
            raise ValueError("description cannot be null")
        return self


class EvidenceReorder(BaseModel):
    evidence_ids: list[int] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def reject_duplicates(self) -> "EvidenceReorder":
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("evidence_ids cannot contain duplicates")
        return self
