from functools import lru_cache

from fastapi import APIRouter, File, Form, UploadFile, status

from app.ai.errors import AIError
from app.ai.models import AIModel, GenerationResult, ModelCapabilities
from app.ai.service import AIService
from app.schemas.ai import (
    AICapabilitiesResponse,
    AIModelResponse,
    AISettingsResponse,
    AISettingsUpdate,
    AIStatusResponse,
    CancelResponse,
    GenerationResponse,
    GenerateTextRequest,
)

router = APIRouter(prefix="/api/ai", tags=["local-ai"])


@lru_cache
def get_ai_service() -> AIService:
    return AIService()


@router.get("/settings", response_model=AISettingsResponse)
async def get_ai_settings() -> AISettingsResponse:
    return AISettingsResponse.model_validate(get_ai_service().config(), from_attributes=True)


@router.patch("/settings", response_model=AISettingsResponse)
async def update_ai_settings(payload: AISettingsUpdate) -> AISettingsResponse:
    config = await get_ai_service().update_config(enabled=payload.enabled, model=payload.model)
    return AISettingsResponse.model_validate(config, from_attributes=True)


@router.get("/status", response_model=AIStatusResponse)
async def get_ai_status() -> AIStatusResponse:
    service = get_ai_service()
    config = service.config()
    if not config.enabled:
        return _status_response(config.enabled, config.model, False, None, [], None, "A IA está desativada.")
    try:
        config, provider_status, capabilities = await service.status()
        return _status_response(
            True,
            config.model,
            provider_status.available,
            provider_status.version,
            provider_status.models,
            capabilities,
            provider_status.error,
        )
    except AIError as exc:
        return _status_response(True, config.model, False, None, [], None, exc.detail)


@router.get("/models", response_model=list[AIModelResponse])
async def list_ai_models() -> list[AIModelResponse]:
    return [_model_response(model) for model in await get_ai_service().models()]


@router.post("/test-connection", response_model=AIStatusResponse)
async def test_ai_connection() -> AIStatusResponse:
    return await get_ai_status()


@router.post("/test-generation", response_model=GenerationResponse)
async def test_ai_generation() -> GenerationResponse:
    result = await get_ai_service().generate_text(
        "Responda somente com uma frase curta confirmando que a geração local está funcionando."
    )
    return _generation_response(result)


@router.post("/generate/text", response_model=GenerationResponse)
async def generate_text(payload: GenerateTextRequest) -> GenerationResponse:
    return _generation_response(await get_ai_service().generate_text(payload.prompt))


@router.post("/generate/images", response_model=GenerationResponse)
async def generate_images(
    prompt: str = Form(min_length=1, max_length=50_000),
    images: list[UploadFile] = File(...),
) -> GenerationResponse:
    inputs = [(await image.read(), image.content_type) for image in images]
    return _generation_response(await get_ai_service().generate_images(prompt, inputs))


@router.delete("/operations/current", response_model=CancelResponse, status_code=status.HTTP_200_OK)
async def cancel_ai_operation() -> CancelResponse:
    return CancelResponse(cancelled=await get_ai_service().cancel_current())


def _status_response(
    enabled: bool,
    selected_model: str,
    available: bool,
    version: str | None,
    models: list[AIModel],
    capabilities: ModelCapabilities | None,
    error: str | None,
) -> AIStatusResponse:
    return AIStatusResponse(
        enabled=enabled,
        available=available,
        version=version,
        selected_model=selected_model,
        selected_model_installed=selected_model in {model.name for model in models},
        capabilities=_capabilities_response(capabilities) if capabilities else None,
        error=error,
    )


def _model_response(model: AIModel) -> AIModelResponse:
    return AIModelResponse(
        name=model.name,
        size=model.size,
        modified_at=model.modified_at,
        capabilities=_capabilities_response(model.capabilities) if model.capabilities else None,
    )


def _capabilities_response(capabilities: ModelCapabilities) -> AICapabilitiesResponse:
    return AICapabilitiesResponse(
        text=capabilities.text,
        images=capabilities.images,
        declared=list(capabilities.declared),
    )


def _generation_response(result: GenerationResult) -> GenerationResponse:
    return GenerationResponse(model=result.model, text=result.text, done=result.done)
