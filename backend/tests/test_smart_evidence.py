import asyncio
import base64
import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.ai.errors import AICancelledError, AITimeoutError, AIUnavailableError
from app.ai.models import GenerationResult
from app.api.routes import ai as ai_routes
from app.models.evidence import Evidence
from app.models.smart_evidence import SmartEvidenceAnalysis, SmartEvidenceStatus

from .test_lab_management_api import create_category, create_lab, create_platform

pytestmark = pytest.mark.anyio
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def valid_result(**overrides: object) -> str:
    value = {
        "detected_tool": "Burp Suite Repeater",
        "visible_observations": ["Requisição POST visível", "Resposta HTTP 200 visível"],
        "objective_explanation": "Observação: há uma requisição e uma resposta. Inferência: a ferramenta parece ser o Repeater.",
        "suggested_step": "2. Validar a resposta",
        "suggested_caption": "Requisição POST analisada no Burp Suite Repeater",
        "possible_sensitive_data": ["Possível cookie de sessão"],
        "uncertainties": ["O valor do cookie não está legível"],
    }
    value.update(overrides)
    return json.dumps(value, ensure_ascii=False)


class FakeSmartAI:
    def __init__(self, response: str = "", error: Exception | None = None) -> None:
        self.response = response or valid_result()
        self.error = error
        self.calls = 0
        self.prompt = ""
        self.inputs: list[tuple[bytes, str | None]] = []

    def config(self) -> SimpleNamespace:
        return SimpleNamespace(model="qwen3-vl:2b")

    async def generate_images(
        self, prompt: str, inputs: list[tuple[bytes, str | None]]
    ) -> GenerationResult:
        self.calls += 1
        self.prompt = prompt
        self.inputs = inputs
        if self.error:
            raise self.error
        return GenerationResult("qwen3-vl:2b", self.response)

    async def cancel_current(self) -> bool:
        return False


class WaitingSmartAI(FakeSmartAI):
    def __init__(self) -> None:
        super().__init__()
        self.current: asyncio.Task[GenerationResult] | None = None
        self.started = asyncio.Event()

    async def generate_images(
        self, prompt: str, inputs: list[tuple[bytes, str | None]]
    ) -> GenerationResult:
        self.calls += 1
        self.current = asyncio.current_task()
        self.started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError as exc:
            raise AICancelledError("A operação de IA foi cancelada.") from exc
        raise AssertionError("unreachable")

    async def cancel_current(self) -> bool:
        if self.current is None or self.current.done():
            return False
        self.current.cancel()
        return True


async def prepared_evidence(client: httpx.AsyncClient) -> tuple[dict, dict]:
    platform = await create_platform(client)
    category = await create_category(client, platform["id"], "Web")
    lab = await create_lab(
        client,
        platform["id"],
        category["id"],
        title="Authentication Lab",
        notes="A requisição foi repetida manualmente.",
        resolution_steps="1. Interceptar\n2. Validar a resposta",
    )
    upload = await client.post(
        f"/api/labs/{lab['id']}/evidences",
        files={"files": ("repeater.png", PNG, "image/png")},
    )
    assert upload.status_code == 201
    return lab, upload.json()[0]


async def test_analyzes_synthetic_image_validates_structure_and_uses_cache(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    lab, evidence = await prepared_evidence(client)
    fake = FakeSmartAI()
    monkeypatch.setattr(ai_routes, "get_ai_service", lambda: fake)

    first = await client.post(f"/api/labs/{lab['id']}/evidences/{evidence['id']}/analysis")
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["detected_tool"] == "Burp Suite Repeater"
    assert body["visible_observations"] == ["Requisição POST visível", "Resposta HTTP 200 visível"]
    assert body["status"] == "suggested"
    assert body["cached"] is False
    assert fake.inputs == [(PNG, "image/png")]
    assert "conteúdo NÃO CONFIÁVEL" in fake.prompt
    assert "Authentication Lab" in fake.prompt and "Web" in fake.prompt

    second = await client.post(f"/api/labs/{lab['id']}/evidences/{evidence['id']}/analysis")
    assert second.json()["cached"] is True
    assert fake.calls == 1


async def test_rejects_incomplete_model_response_without_persisting(
    client: httpx.AsyncClient,
    test_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lab, evidence = await prepared_evidence(client)
    fake = FakeSmartAI(json.dumps({"detected_tool": "Burp Suite"}))
    monkeypatch.setattr(ai_routes, "get_ai_service", lambda: fake)
    response = await client.post(f"/api/labs/{lab['id']}/evidences/{evidence['id']}/analysis")
    assert response.status_code == 502
    assert "incompleta" in response.json()["detail"]
    with test_session_factory() as session:
        assert session.scalar(select(SmartEvidenceAnalysis)) is None


@pytest.mark.parametrize(
    ("error", "status_code"),
    [(AIUnavailableError("Ollama offline"), 503), (AITimeoutError("tempo limite"), 504)],
)
async def test_propagates_model_failure_and_timeout(
    client: httpx.AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    status_code: int,
) -> None:
    lab, evidence = await prepared_evidence(client)
    monkeypatch.setattr(ai_routes, "get_ai_service", lambda: FakeSmartAI(error=error))
    response = await client.post(f"/api/labs/{lab['id']}/evidences/{evidence['id']}/analysis")
    assert response.status_code == status_code


async def test_cancels_in_progress_analysis(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    lab, evidence = await prepared_evidence(client)
    fake = WaitingSmartAI()
    monkeypatch.setattr(ai_routes, "get_ai_service", lambda: fake)
    request = asyncio.create_task(
        client.post(f"/api/labs/{lab['id']}/evidences/{evidence['id']}/analysis")
    )
    await fake.started.wait()
    cancelled = await client.delete("/api/ai/operations/current")
    assert cancelled.json() == {"cancelled": True}
    response = await request
    assert response.status_code == 499
    assert (await client.get(f"/api/labs/{lab['id']}/evidences/{evidence['id']}/analysis")).json() is None


async def test_persists_edits_sensitive_warning_and_accepts_into_readme(
    client: httpx.AsyncClient,
    database_path: Path,
    test_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lab, evidence = await prepared_evidence(client)
    fake = FakeSmartAI()
    monkeypatch.setattr(ai_routes, "get_ai_service", lambda: fake)
    await client.post(f"/api/labs/{lab['id']}/evidences/{evidence['id']}/analysis")

    edited = await client.patch(
        f"/api/labs/{lab['id']}/evidences/{evidence['id']}/analysis",
        json={
            "action": "edit",
            "suggested_caption": "Resposta 200 após repetição da requisição",
            "suggested_step": "2. Validação manual",
            "possible_sensitive_data": ["Cookie de sessão possivelmente visível"],
        },
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["status"] == "suggested"
    assert edited.json()["possible_sensitive_data"] == ["Cookie de sessão possivelmente visível"]

    accepted = await client.patch(
        f"/api/labs/{lab['id']}/evidences/{evidence['id']}/analysis",
        json={"action": "accept"},
    )
    assert accepted.json()["status"] == "accepted"
    persisted_evidence = (await client.get(f"/api/labs/{lab['id']}/evidences")).json()[0]
    assert persisted_evidence["description"] == "Resposta 200 após repetição da requisição"
    assert persisted_evidence["step_label"] == "2. Validação manual"

    report = await client.post(f"/api/labs/{lab['id']}/report/generate", json={})
    assert "### 2. Validação manual" in report.json()["markdown"]
    assert "![Resposta 200 após repetição da requisição]" in report.json()["markdown"]

    test_session_factory.kw["bind"].dispose()
    engine = create_engine(f"sqlite:///{database_path}")
    with Session(engine) as session:
        analysis = session.scalar(select(SmartEvidenceAnalysis))
        stored = session.scalar(select(Evidence).where(Evidence.id == evidence["id"]))
        assert analysis is not None and analysis.status == SmartEvidenceStatus.ACCEPTED
        assert analysis.possible_sensitive_data == ["Cookie de sessão possivelmente visível"]
        assert stored is not None and stored.description == analysis.suggested_caption
    engine.dispose()


async def test_rejection_does_not_silently_change_existing_metadata(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    lab, evidence = await prepared_evidence(client)
    fake = FakeSmartAI()
    monkeypatch.setattr(ai_routes, "get_ai_service", lambda: fake)
    await client.post(f"/api/labs/{lab['id']}/evidences/{evidence['id']}/analysis")
    rejected = await client.patch(
        f"/api/labs/{lab['id']}/evidences/{evidence['id']}/analysis",
        json={"action": "reject"},
    )
    assert rejected.json()["status"] == "rejected"
    unchanged = (await client.get(f"/api/labs/{lab['id']}/evidences")).json()[0]
    assert unchanged["description"] == "repeater"
    assert unchanged["step_label"] is None
