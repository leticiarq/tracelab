import asyncio
from collections.abc import Callable

from app.ai.config import AIConfig, AIConfigRepository
from app.ai.errors import (
    AIBusyError,
    AICancelledError,
    AIDisabledError,
    AIIncompatibleModelError,
    AIModelNotFoundError,
)
from app.ai.images import prepare_images
from app.ai.models import AIModel, GenerationResult, ModelCapabilities, ProviderStatus
from app.ai.ollama import OllamaProvider
from app.ai.ollama_client import OllamaClient
from app.ai.provider import AIProvider
from app.core.config import Settings, settings

ProviderFactory = Callable[[AIConfig], AIProvider]


class AIService:
    def __init__(
        self,
        config_repository: AIConfigRepository | None = None,
        provider_factory: ProviderFactory | None = None,
        app_settings: Settings = settings,
    ) -> None:
        self.config_repository = config_repository or AIConfigRepository(app_settings)
        self.provider_factory = provider_factory or self._ollama_factory
        self.settings = app_settings
        self._operation_lock = asyncio.Lock()
        self._current_task: asyncio.Task[GenerationResult] | None = None

    def config(self) -> AIConfig:
        return self.config_repository.load()

    async def update_config(self, *, enabled: bool | None, model: str | None) -> AIConfig:
        if model is not None:
            model = model.strip()
            if not model:
                raise AIModelNotFoundError("Selecione um modelo válido.")
            config = self.config()
            provider = self.provider_factory(config)
            try:
                models = await provider.list_models()
                if model not in {item.name for item in models}:
                    raise AIModelNotFoundError("O modelo selecionado não está instalado no Ollama.")
                await provider.capabilities(model)
            finally:
                await provider.close()
        return self.config_repository.save(enabled=enabled, model=model)

    async def status(self) -> tuple[AIConfig, ProviderStatus, ModelCapabilities | None]:
        config = self.config()
        if not config.enabled:
            return config, ProviderStatus(available=False, error="A IA está desativada."), None
        provider = self.provider_factory(config)
        try:
            status = await provider.status()
            capabilities = None
            if config.model in {model.name for model in status.models}:
                capabilities = await provider.capabilities(config.model)
            return config, status, capabilities
        finally:
            await provider.close()

    async def models(self) -> list[AIModel]:
        config = self._require_enabled()
        provider = self.provider_factory(config)
        try:
            models = await provider.list_models()
            enriched: list[AIModel] = []
            for model in models:
                capabilities = await provider.capabilities(model.name)
                enriched.append(AIModel(model.name, model.size, model.modified_at, capabilities))
            return enriched
        finally:
            await provider.close()

    async def generate_text(self, prompt: str) -> GenerationResult:
        return await self._generate(prompt, [])

    async def generate_images(
        self, prompt: str, inputs: list[tuple[bytes, str | None]]
    ) -> GenerationResult:
        prepared = prepare_images(
            inputs,
            max_images=self.settings.ai_max_images,
            max_bytes=self.settings.ai_max_image_bytes,
            max_dimension=self.settings.ai_max_image_dimension,
        )
        return await self._generate(prompt, [image.content for image in prepared])

    async def cancel_current(self) -> bool:
        task = self._current_task
        if task is None or task.done():
            return False
        task.cancel()
        return True

    async def _generate(self, prompt: str, images: list[bytes]) -> GenerationResult:
        config = self._require_enabled()
        if self._operation_lock.locked():
            raise AIBusyError("Já existe uma operação de IA em andamento.")
        async with self._operation_lock:
            provider = self.provider_factory(config)
            try:
                capabilities = await provider.capabilities(config.model)
                if not capabilities.text:
                    raise AIIncompatibleModelError("O modelo selecionado não oferece geração de texto.")
                if images and not capabilities.images:
                    raise AIIncompatibleModelError("O modelo selecionado não oferece suporte a imagens.")
                self._current_task = asyncio.create_task(
                    provider.generate(config.model, prompt, images or None, config.keep_alive)
                )
                try:
                    return await self._current_task
                except asyncio.CancelledError as exc:
                    raise AICancelledError("A operação de IA foi cancelada.") from exc
                finally:
                    self._current_task = None
            finally:
                await provider.close()

    def _require_enabled(self) -> AIConfig:
        config = self.config()
        if not config.enabled:
            raise AIDisabledError("A IA está desativada nas configurações.")
        return config

    @staticmethod
    def _ollama_factory(config: AIConfig) -> AIProvider:
        return OllamaProvider(OllamaClient(config.base_url, config.timeout_seconds))
