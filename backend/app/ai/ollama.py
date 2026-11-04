import base64
from datetime import datetime
from typing import Any

from app.ai.errors import AIInvalidResponseError
from app.ai.models import AIModel, GenerationResult, ModelCapabilities, ProviderStatus
from app.ai.ollama_client import OllamaClient
from app.ai.provider import AIProvider


class OllamaProvider(AIProvider):
    def __init__(self, client: OllamaClient) -> None:
        self.client = client

    async def status(self) -> ProviderStatus:
        version_payload = await self.client.get_version()
        models = await self.list_models()
        version = version_payload.get("version")
        return ProviderStatus(
            available=True,
            version=version if isinstance(version, str) else None,
            models=models,
        )

    async def list_models(self) -> list[AIModel]:
        payload = await self.client.get_tags()
        entries = payload.get("models")
        if not isinstance(entries, list):
            raise AIInvalidResponseError("O Ollama retornou uma lista de modelos inválida.")
        models: list[AIModel] = []
        for entry in entries:
            if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
                raise AIInvalidResponseError("O Ollama retornou dados inválidos para um modelo.")
            modified = _parse_datetime(entry.get("modified_at"))
            size = entry.get("size")
            models.append(AIModel(entry["name"], size if isinstance(size, int) else None, modified))
        return models

    async def capabilities(self, model: str) -> ModelCapabilities:
        payload = await self.client.show(model)
        raw = payload.get("capabilities", [])
        declared = tuple(value for value in raw if isinstance(value, str)) if isinstance(raw, list) else ()
        # Older Ollama versions omitted capabilities. Text generation remains the
        # compatible fallback, but image support must always be explicitly declared.
        text = "completion" in declared or not declared
        return ModelCapabilities(text=text, images="vision" in declared, declared=declared)

    async def generate(
        self,
        model: str,
        prompt: str,
        images: list[bytes] | None = None,
        keep_alive: str | int | None = None,
    ) -> GenerationResult:
        encoded = [base64.b64encode(image).decode("ascii") for image in images or []]
        payload = await self.client.generate(model, prompt, encoded or None, keep_alive)
        response = payload.get("response")
        if not isinstance(response, str) or not response.strip():
            raise AIInvalidResponseError("O Ollama retornou uma geração vazia ou inválida.")
        returned_model = payload.get("model")
        done = payload.get("done", True)
        return GenerationResult(
            model=returned_model if isinstance(returned_model, str) else model,
            text=response,
            done=done if isinstance(done, bool) else True,
        )

    async def close(self) -> None:
        await self.client.close()


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
