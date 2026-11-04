from typing import Any

import httpx

from app.ai.errors import (
    AIInvalidResponseError,
    AIModelNotFoundError,
    AITimeoutError,
    AIUnavailableError,
)


class OllamaClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"),
            timeout=httpx.Timeout(timeout_seconds),
            transport=transport,
        )

    async def get_version(self) -> dict[str, Any]:
        return await self._request("GET", "/api/version")

    async def get_tags(self) -> dict[str, Any]:
        return await self._request("GET", "/api/tags")

    async def show(self, model: str) -> dict[str, Any]:
        return await self._request("POST", "/api/show", json={"model": model})

    async def generate(
        self,
        model: str,
        prompt: str,
        images: list[str] | None,
        keep_alive: str | int | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"model": model, "prompt": prompt, "stream": False}
        if images:
            payload["images"] = images
        if keep_alive is not None:
            payload["keep_alive"] = keep_alive
        return await self._request("POST", "/api/generate", json=payload)

    async def close(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = await self._client.request(method, path, **kwargs)
        except httpx.TimeoutException as exc:
            raise AITimeoutError("O Ollama excedeu o tempo limite configurado.") from exc
        except httpx.RequestError as exc:
            raise AIUnavailableError(
                "O Ollama não está disponível. Confirme se o serviço local está em execução."
            ) from exc

        if response.status_code == 404 and path == "/api/show":
            raise AIModelNotFoundError("O modelo selecionado não está instalado no Ollama.")
        if response.is_error:
            try:
                detail = response.json().get("error")
            except (ValueError, AttributeError):
                detail = None
            raise AIUnavailableError(detail or f"O Ollama retornou HTTP {response.status_code}.")
        try:
            payload = response.json()
        except ValueError as exc:
            raise AIInvalidResponseError("O Ollama retornou uma resposta que não é JSON válido.") from exc
        if not isinstance(payload, dict):
            raise AIInvalidResponseError("O Ollama retornou um formato de resposta inválido.")
        return payload
