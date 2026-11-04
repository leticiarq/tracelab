from datetime import datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.lab import LabStatus
from app.schemas.validators import validate_http_url


class LabBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    platform_id: int = Field(ge=1)
    category_id: int | None = Field(default=None, ge=1)
    source_url: str | None = Field(default=None, max_length=2048)
    difficulty: str | None = Field(default=None, min_length=1, max_length=50)
    status: LabStatus = LabStatus.TODO
    notes: str = Field(default="", max_length=100_000)
    objective: str | None = Field(default=None, max_length=100_000)
    vulnerability_description: str | None = Field(default=None, max_length=100_000)
    impact: str | None = Field(default=None, max_length=100_000)
    mitigation: str | None = Field(default=None, max_length=100_000)
    learnings: str | None = Field(default=None, max_length=100_000)
    resolution_steps: str | None = Field(default=None, max_length=100_000)

    model_config = ConfigDict(str_strip_whitespace=True)
    _validate_source_url = field_validator("source_url", mode="before")(validate_http_url)


class LabCreate(LabBase):
    pass


class LabUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    platform_id: int | None = Field(default=None, ge=1)
    category_id: int | None = Field(default=None, ge=1)
    source_url: str | None = Field(default=None, max_length=2048)
    difficulty: str | None = Field(default=None, min_length=1, max_length=50)
    status: LabStatus | None = None
    notes: str | None = Field(default=None, max_length=100_000)
    objective: str | None = Field(default=None, max_length=100_000)
    vulnerability_description: str | None = Field(default=None, max_length=100_000)
    impact: str | None = Field(default=None, max_length=100_000)
    mitigation: str | None = Field(default=None, max_length=100_000)
    learnings: str | None = Field(default=None, max_length=100_000)
    resolution_steps: str | None = Field(default=None, max_length=100_000)

    model_config = ConfigDict(str_strip_whitespace=True)
    _validate_source_url = field_validator("source_url", mode="before")(validate_http_url)

    @model_validator(mode="after")
    def reject_null_required_fields(self) -> Self:
        for field in ("title", "platform_id", "status", "notes"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class LabRead(LabBase):
    id: int
    slug: str
    created_at: datetime
    updated_at: datetime
    solved_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
