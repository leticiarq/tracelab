import asyncio
import io
from pathlib import Path

import httpx
import pytest
from PIL import Image

from app.ai.config import AIConfigRepository
from app.ai.errors import (
    AIBusyError,
    AICancelledError,
    AIIncompatibleModelError,
    AIInvalidResponseError,
    AITimeoutError,
)
from app.ai.models import AIModel, GenerationResult, ModelCapabilities, ProviderStatus
from app.ai.ollama import OllamaProvider
from app.ai.ollama_client import OllamaClient
from app.ai.provider import AIProvider
from app.ai.service import AIService
from app.api.routes import ai as ai_routes
from app.core.config import settings

pytestmark = pytest.mark.anyio


class FakeProvider(AIProvider):
    def __init__(
        self,
        *,
        capabilities: ModelCapabilities | None = None,
        generation: GenerationResult | None = None,
        wait: asyncio.Event | None = None,
    ) -> None:
        self.model_capabilities = capabilities or ModelCapabilities(True, True, ("completion", "vision"))
        self.generation = generation or GenerationResult("qwen3-vl:2b", "Tudo certo.")
        self.wait = wait
        self.received_images: list[bytes] | None = None
        self.closed = False

    async def status(self) -> ProviderStatus:
        return ProviderStatus(True, "0.12.0", models=[AIModel("qwen3-vl:2b", 1_500_000)])

    async def list_models(self) -> list[AIModel]:
        return [AIModel("qwen3-vl:2b", 1_500_000)]

    async def capabilities(self, model: str) -> ModelCapabilities:
        return self.model_capabilities

    async def generate(self, model: str, prompt: str, images=None, keep_alive=None) -> GenerationResult:
        self.received_images = images
        if self.wait is not None:
            await self.wait.wait()
        return self.generation

    async def close(self) -> None:
        self.closed = True


@pytest.fixture
def ai_repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AIConfigRepository:
    monkeypatch.setattr(settings, "ai_config_path", tmp_path / "ai-settings.json")
    monkeypatch.setattr(settings, "ai_enabled", True)
    monkeypatch.setattr(settings, "ollama_model", "qwen3-vl:2b")
    return AIConfigRepository(settings)


async def test_ollama_provider_lists_models_and_generates_text_with_mock() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "qwen3-vl:2b", "size": 42}]})
        if request.url.path == "/api/show":
            return httpx.Response(200, json={"capabilities": ["completion", "vision"]})
        if request.url.path == "/api/generate":
            return httpx.Response(200, json={"model": "qwen3-vl:2b", "response": "Resposta local", "done": True})
        return httpx.Response(200, json={"version": "0.12.0"})

    provider = OllamaProvider(OllamaClient("http://ollama.test", 2, httpx.MockTransport(handler)))
    assert [model.name for model in await provider.list_models()] == ["qwen3-vl:2b"]
    assert (await provider.capabilities("qwen3-vl:2b")).images is True
    assert (await provider.generate("qwen3-vl:2b", "Olá")).text == "Resposta local"
    await provider.close()


async def test_ollama_timeout_is_translated() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow")

    client = OllamaClient("http://ollama.test", 0.01, httpx.MockTransport(handler))
    with pytest.raises(AITimeoutError, match="tempo limite"):
        await client.get_tags()
    await client.close()


async def test_ollama_invalid_response_is_rejected() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(200, text="not-json"))
    client = OllamaClient("http://ollama.test", 2, transport)
    with pytest.raises(AIInvalidResponseError, match="não é JSON"):
        await client.get_tags()
    await client.close()


async def test_model_without_declared_vision_rejects_images(ai_repository: AIConfigRepository) -> None:
    provider = FakeProvider(capabilities=ModelCapabilities(True, False, ("completion",)))
    service = AIService(ai_repository, lambda _: provider, settings)
    image = io.BytesIO()
    Image.new("RGB", (20, 20), "white").save(image, "PNG")
    with pytest.raises(AIIncompatibleModelError, match="suporte a imagens"):
        await service.generate_images("Descreva", [(image.getvalue(), "image/png")])


async def test_duplicate_large_images_are_resized_once(ai_repository: AIConfigRepository, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ai_max_image_dimension", 100)
    provider = FakeProvider()
    service = AIService(ai_repository, lambda _: provider, settings)
    image = io.BytesIO()
    Image.new("RGB", (300, 200), "white").save(image, "PNG")
    content = image.getvalue()
    await service.generate_images("Leia", [(content, "image/png"), (content, "image/png")])
    assert provider.received_images is not None and len(provider.received_images) == 1
    with Image.open(io.BytesIO(provider.received_images[0])) as resized:
        assert max(resized.size) == 100


async def test_generation_can_be_cancelled_and_parallel_request_is_rejected(ai_repository: AIConfigRepository) -> None:
    wait = asyncio.Event()
    provider = FakeProvider(wait=wait)
    service = AIService(ai_repository, lambda _: provider, settings)
    first = asyncio.create_task(service.generate_text("Primeira"))
    await asyncio.sleep(0)
    with pytest.raises(AIBusyError):
        await service.generate_text("Segunda")
    assert await service.cancel_current() is True
    with pytest.raises(AICancelledError):
        await first


async def test_ai_api_works_with_mocked_ollama(client: httpx.AsyncClient, ai_repository: AIConfigRepository, monkeypatch: pytest.MonkeyPatch) -> None:
    service = AIService(ai_repository, lambda _: FakeProvider(), settings)
    monkeypatch.setattr(ai_routes, "get_ai_service", lambda: service)

    status_response = await client.post("/api/ai/test-connection")
    assert status_response.status_code == 200
    assert status_response.json()["available"] is True
    assert status_response.json()["capabilities"] == {
        "text": True,
        "images": True,
        "declared": ["completion", "vision"],
    }

    generation_response = await client.post("/api/ai/generate/text", json={"prompt": "Olá"})
    assert generation_response.status_code == 200
    assert generation_response.json()["text"] == "Tudo certo."


async def test_ai_api_remains_usable_when_ollama_is_unavailable(client: httpx.AsyncClient, ai_repository: AIConfigRepository, monkeypatch: pytest.MonkeyPatch) -> None:
    class OfflineProvider(FakeProvider):
        async def status(self) -> ProviderStatus:
            from app.ai.errors import AIUnavailableError
            raise AIUnavailableError("Ollama offline")

    service = AIService(ai_repository, lambda _: OfflineProvider(), settings)
    monkeypatch.setattr(ai_routes, "get_ai_service", lambda: service)
    response = await client.get("/api/ai/status")
    assert response.status_code == 200
    assert response.json()["available"] is False
    assert response.json()["error"] == "Ollama offline"
    assert (await client.get("/health")).status_code == 200


async def test_ai_can_be_disabled_without_contacting_provider(client: httpx.AsyncClient, ai_repository: AIConfigRepository, monkeypatch: pytest.MonkeyPatch) -> None:
    called = False

    def factory(_):
        nonlocal called
        called = True
        return FakeProvider()

    service = AIService(ai_repository, factory, settings)
    monkeypatch.setattr(ai_routes, "get_ai_service", lambda: service)
    response = await client.patch("/api/ai/settings", json={"enabled": False})
    assert response.status_code == 200
    status_response = await client.get("/api/ai/status")
    assert status_response.json()["enabled"] is False
    assert called is False
    generation = await client.post("/api/ai/generate/text", json={"prompt": "Olá"})
    assert generation.status_code == 503
