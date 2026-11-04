import base64

import httpx
import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.ai.errors import AITimeoutError
from app.ai.models import GenerationResult
from app.api.routes import reports as report_routes
from app.core.config import Settings
from app.models.smart_evidence import SmartEvidenceAnalysis, SmartEvidenceStatus

from .test_lab_management_api import create_category, create_lab, create_platform

pytestmark = pytest.mark.anyio
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def test_ollama_configuration_rejects_external_hosts() -> None:
    with pytest.raises(ValueError, match="URL local"):
        Settings(ollama_base_url="https://ollama.example.com")
    assert Settings(ollama_base_url="http://localhost:11434/").ollama_base_url == "http://localhost:11434"


class StubAIService:
    def __init__(self, text: str) -> None:
        self.text = text
        self.prompt = ""

    async def generate_text(self, prompt: str) -> GenerationResult:
        self.prompt = prompt
        return GenerationResult("qwen-local:latest", self.text)


async def lab_with_notes(client: httpx.AsyncClient) -> dict:
    platform = await create_platform(client)
    category = await create_category(client, platform["id"])
    return await create_lab(
        client,
        platform["id"],
        category["id"],
        title="Authentication Lab",
        notes="eu usei o proxy e depois vi resposta 200",
        objective="Avaliar o controle de acesso.",
        vulnerability_description="Possível falha de autorização.",
        resolution_steps="Interceptei a requisição e observei a resposta.",
    )


async def test_ai_suggestion_is_persisted_reviewed_and_never_replaces_notes(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    lab = await lab_with_notes(client)
    stub = StubAIService(
        '{"suggestion":"Usei um proxy e observei uma resposta HTTP 200.",'
        '"ambiguities":["O proxy não foi identificado."],'
        '"questions":["Qual ferramenta de proxy foi utilizada?"]}'
    )
    monkeypatch.setattr(report_routes, "get_ai_service", lambda: stub)

    generated = await client.post(
        f"/api/labs/{lab['id']}/report/ai/generate",
        json={"action": "improve_notes", "style": "professional", "evidence_ids": []},
    )
    assert generated.status_code == 200, generated.text
    version = generated.json()
    assert version["original_text"] == lab["notes"]
    assert version["status"] == "suggested"
    assert (await client.get(f"/api/labs/{lab['id']}")).json()["notes"] == lab["notes"]

    reviewed = await client.patch(
        f"/api/labs/{lab['id']}/report/ai/versions/{version['id']}",
        json={"action": "accept"},
    )
    assert reviewed.json()["status"] == "accepted"
    persisted = (await client.get(f"/api/labs/{lab['id']}/report/ai/versions")).json()
    assert persisted[0]["suggested_text"].startswith("Usei um proxy")
    assert (await client.get(f"/api/labs/{lab['id']}")).json()["notes"] == lab["notes"]


async def test_readme_uses_relative_evidence_path_and_only_approved_analysis(
    client: httpx.AsyncClient,
    test_session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lab = await lab_with_notes(client)
    evidence = (
        await client.post(
            f"/api/labs/{lab['id']}/evidences",
            files={"files": ("proof.png", PNG, "image/png")},
        )
    ).json()[0]
    with test_session_factory() as db:
        db.add(
            SmartEvidenceAnalysis(
                evidence_id=evidence["id"],
                image_sha256=evidence["sha256"],
                model_name="vision-local",
                instruction_version="test",
                context_hash="a" * 64,
                detected_tool=None,
                visible_observations=["Resposta HTTP 200 visível"],
                objective_explanation="Fato observado: código 200 visível.",
                suggested_step=None,
                suggested_caption="Resposta observada",
                possible_sensitive_data=[],
                uncertainties=[],
                status=SmartEvidenceStatus.ACCEPTED,
            )
        )
        db.commit()
    stub = StubAIService(
        '{"suggestion":"# Authentication Lab\\n\\n## 5. Evidências\\n\\n![Resposta](evidence/image-01.png)",'
        '"ambiguities":[],"questions":[]}'
    )
    monkeypatch.setattr(report_routes, "get_ai_service", lambda: stub)
    response = await client.post(
        f"/api/labs/{lab['id']}/report/ai/generate",
        json={"action": "generate_readme", "style": "github", "evidence_ids": [evidence["id"]]},
    )
    assert response.status_code == 200, response.text
    assert "evidence/image-01.png" in stub.prompt
    assert "Resposta HTTP 200 visível" in stub.prompt
    assert "dados_nao_confiaveis" in stub.prompt


async def test_invalid_model_response_and_timeout_do_not_create_versions(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    lab = await lab_with_notes(client)
    invalid = StubAIService("not-json")
    monkeypatch.setattr(report_routes, "get_ai_service", lambda: invalid)
    response = await client.post(
        f"/api/labs/{lab['id']}/report/ai/generate",
        json={"action": "generate_readme", "style": "study", "evidence_ids": []},
    )
    assert response.status_code == 502
    assert (await client.get(f"/api/labs/{lab['id']}/report/ai/versions")).json() == []

    class TimeoutService:
        async def generate_text(self, _: str) -> GenerationResult:
            raise AITimeoutError("O Ollama excedeu o tempo limite configurado.")

    monkeypatch.setattr(report_routes, "get_ai_service", lambda: TimeoutService())
    timed_out = await client.post(
        f"/api/labs/{lab['id']}/report/ai/generate",
        json={"action": "missing_information", "style": "professional", "evidence_ids": []},
    )
    assert timed_out.status_code == 504
    assert (await client.get(f"/api/labs/{lab['id']}/report/ai/versions")).json() == []


async def test_ai_markdown_can_be_edited_saved_and_exported_without_overwriting_notes(
    client: httpx.AsyncClient,
) -> None:
    lab = await lab_with_notes(client)
    markdown = "# Authentication Lab\n\nConteúdo revisado pelo usuário.\n"
    saved = await client.put(f"/api/labs/{lab['id']}/report", json={"markdown": markdown})
    assert saved.status_code == 200, saved.text
    assert saved.json()["markdown"] == markdown
    exported = await client.post(
        f"/api/labs/{lab['id']}/report/export",
        json={"evidence_ids": [], "sensitive_reviewed": True},
    )
    assert exported.status_code == 200
    assert (await client.get(f"/api/labs/{lab['id']}")).json()["notes"] == lab["notes"]
