from abc import ABC, abstractmethod

from app.ai.models import AIModel, GenerationResult, ModelCapabilities, ProviderStatus


class AIProvider(ABC):
    @abstractmethod
    async def status(self) -> ProviderStatus:
        raise NotImplementedError

    @abstractmethod
    async def list_models(self) -> list[AIModel]:
        raise NotImplementedError

    @abstractmethod
    async def capabilities(self, model: str) -> ModelCapabilities:
        raise NotImplementedError

    @abstractmethod
    async def generate(
        self,
        model: str,
        prompt: str,
        images: list[bytes] | None = None,
        keep_alive: str | int | None = None,
    ) -> GenerationResult:
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        raise NotImplementedError
