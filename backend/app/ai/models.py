from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class ModelCapabilities:
    text: bool
    images: bool
    declared: tuple[str, ...] = ()


@dataclass(frozen=True)
class AIModel:
    name: str
    size: int | None = None
    modified_at: datetime | None = None
    capabilities: ModelCapabilities | None = None


@dataclass(frozen=True)
class GenerationResult:
    model: str
    text: str
    done: bool = True


@dataclass(frozen=True)
class PreparedImage:
    content: bytes
    media_type: str
    digest: str


@dataclass(frozen=True)
class ProviderStatus:
    available: bool
    version: str | None = None
    error: str | None = None
    models: list[AIModel] = field(default_factory=list)
