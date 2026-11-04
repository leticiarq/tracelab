from datetime import datetime

from pydantic import BaseModel, Field


class AISettingsResponse(BaseModel):
    enabled: bool
    model: str
    timeout_seconds: float
    keep_alive: str
    base_url: str


class AISettingsUpdate(BaseModel):
    enabled: bool | None = None
    model: str | None = Field(default=None, max_length=200)


class AICapabilitiesResponse(BaseModel):
    text: bool
    images: bool
    declared: list[str]


class AIModelResponse(BaseModel):
    name: str
    size: int | None
    modified_at: datetime | None
    capabilities: AICapabilitiesResponse | None = None


class AIStatusResponse(BaseModel):
    enabled: bool
    available: bool
    version: str | None
    selected_model: str
    selected_model_installed: bool
    capabilities: AICapabilitiesResponse | None
    error: str | None


class GenerateTextRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=50_000)


class GenerationResponse(BaseModel):
    model: str
    text: str
    done: bool


class CancelResponse(BaseModel):
    cancelled: bool
