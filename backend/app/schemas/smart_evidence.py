from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.smart_evidence import SmartEvidenceStatus

AnalysisListItem = Annotated[str, Field(min_length=1, max_length=1_000)]


class SmartEvidenceResult(BaseModel):
    """Validated structure produced by the local multimodal model."""

    detected_tool: str | None = Field(max_length=200)
    visible_observations: list[AnalysisListItem] = Field(max_length=30)
    objective_explanation: str = Field(min_length=1, max_length=4_000)
    suggested_step: str | None = Field(max_length=200)
    suggested_caption: str = Field(min_length=1, max_length=2_000)
    possible_sensitive_data: list[AnalysisListItem] = Field(max_length=30)
    uncertainties: list[AnalysisListItem] = Field(max_length=30)

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SmartEvidenceRead(SmartEvidenceResult):
    id: int
    evidence_id: int
    image_sha256: str
    model_name: str
    instruction_version: str
    status: SmartEvidenceStatus
    created_at: datetime
    updated_at: datetime
    cached: bool = False

    model_config = ConfigDict(from_attributes=True)


class SmartEvidenceReview(BaseModel):
    action: Literal["edit", "accept", "reject"]
    detected_tool: str | None = Field(default=None, max_length=200)
    visible_observations: list[AnalysisListItem] | None = Field(default=None, max_length=30)
    objective_explanation: str | None = Field(default=None, min_length=1, max_length=4_000)
    suggested_step: str | None = Field(default=None, max_length=200)
    suggested_caption: str | None = Field(default=None, min_length=1, max_length=2_000)
    possible_sensitive_data: list[AnalysisListItem] | None = Field(default=None, max_length=30)
    uncertainties: list[AnalysisListItem] | None = Field(default=None, max_length=30)

    model_config = ConfigDict(str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_action(self) -> Self:
        editable = set(self.model_fields_set) - {"action"}
        if self.action == "reject" and editable:
            raise ValueError("reject does not accept analysis edits")
        return self
