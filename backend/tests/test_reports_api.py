import base64
import io
import zipfile
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.models.report import Report
from app.core.config import settings

from .test_lab_management_api import create_category, create_lab, create_platform

pytestmark = pytest.mark.anyio
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")


async def prepared_lab(client: httpx.AsyncClient, **overrides: object) -> dict:
    platform = await create_platform(client)
    category = await create_category(client, platform["id"])
    return await create_lab(
        client,
        platform["id"],
        category["id"],
        title="SQL Injection Lab",
        objective="Obter acesso administrativo.",
        vulnerability_description="SQL injection no formulário.",
        resolution_steps="1. Interceptar a requisição\n2. Validar o payload",
        impact="Acesso indevido.",
        mitigation="Use consultas parametrizadas.",
        learnings="Validar entradas no servidor.",
        notes="POST /login HTTP/1.1\n\nuser=' OR 1=1--",
        **overrides,
    )


async def test_generates_markdown_preserving_notes_and_image_references(client: httpx.AsyncClient) -> None:
    lab = await prepared_lab(client)
    uploaded = await client.post(
        f"/api/labs/{lab['id']}/evidences",
        files={"files": ("proof.png", PNG, "image/png")},
    )
    evidence = uploaded.json()[0]
    await client.patch(
        f"/api/labs/{lab['id']}/evidences/{evidence['id']}",
        json={"description": "Acesso ao painel", "step_label": "Etapa 2 · Exploração"},
    )

    response = await client.post(f"/api/labs/{lab['id']}/report/generate", json={})
    assert response.status_code == 200, response.text
    body = response.json()
    markdown = body["markdown"]
    assert markdown.startswith("# SQL Injection Lab\n")
    assert "## 1. Informações gerais" in markdown
    assert "## 4. Metodologia e resolução" in markdown
    assert "POST /login HTTP/1.1\n\nuser=' OR 1=1--" in markdown
    assert "### Etapa 2 · Exploração" in markdown
    assert "![Acesso ao painel](evidence/image-01.png)" in markdown
    assert body["incomplete_fields"] == []
    assert (await client.get(f"/api/labs/{lab['id']}/report")).json()["markdown"] == markdown


async def test_omits_empty_sections_and_requires_confirmation_before_regeneration(client: httpx.AsyncClient) -> None:
    platform = await create_platform(client)
    lab = await create_lab(client, platform["id"], notes="Anotação original", objective=None)
    first = await client.post(f"/api/labs/{lab['id']}/report/generate", json={})
    assert first.status_code == 200
    assert "## 2. Objetivo" not in first.json()["markdown"]
    assert "Anotação original" in first.json()["markdown"]
    assert "Objetivo" in first.json()["incomplete_fields"]

    manual = first.json()["markdown"] + "\nEdição manual preservada.\n"
    saved = await client.put(f"/api/labs/{lab['id']}/report", json={"markdown": manual})
    assert saved.status_code == 200
    refused = await client.post(f"/api/labs/{lab['id']}/report/generate", json={})
    assert refused.status_code == 409
    assert (await client.get(f"/api/labs/{lab['id']}/report")).json()["markdown"] == manual
    replaced = await client.post(
        f"/api/labs/{lab['id']}/report/generate", json={"confirm_overwrite": True}
    )
    assert replaced.status_code == 200
    assert "Edição manual preservada" not in replaced.json()["markdown"]


async def test_manual_report_persists_separately_from_notes(
    client: httpx.AsyncClient,
    database_path: Path,
    test_session_factory: sessionmaker[Session],
) -> None:
    lab = await prepared_lab(client)
    await client.post(f"/api/labs/{lab['id']}/report/generate", json={})
    markdown = "# Relatório editado\n\nConteúdo manual."
    assert (await client.put(f"/api/labs/{lab['id']}/report", json={"markdown": markdown})).status_code == 200
    assert (await client.get(f"/api/labs/{lab['id']}")).json()["notes"] == lab["notes"]

    test_session_factory.kw["bind"].dispose()
    engine = create_engine(f"sqlite:///{database_path}")
    with Session(engine) as session:
        persisted = session.scalar(select(Report).where(Report.lab_id == lab["id"]))
        assert persisted is not None and persisted.markdown == markdown
    engine.dispose()


async def test_zip_contains_only_reviewed_lab_files_and_safe_relative_paths(client: httpx.AsyncClient) -> None:
    lab = await prepared_lab(client)
    first = (await client.post(f"/api/labs/{lab['id']}/evidences", files={"files": ("proof.png", PNG, "image/png")})).json()[0]
    await client.post(f"/api/labs/{lab['id']}/report/generate", json={})

    unreviewed = await client.post(
        f"/api/labs/{lab['id']}/report/export",
        json={"evidence_ids": [first["id"]], "sensitive_reviewed": False},
    )
    assert unreviewed.status_code == 422
    missing_reference = await client.post(
        f"/api/labs/{lab['id']}/report/export",
        json={"evidence_ids": [], "sensitive_reviewed": True},
    )
    assert missing_reference.status_code == 422

    exported = await client.post(
        f"/api/labs/{lab['id']}/report/export",
        json={"evidence_ids": [first["id"]], "sensitive_reviewed": True},
    )
    assert exported.status_code == 200, exported.text
    with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
        assert archive.namelist() == [
            "sql-injection-lab/README.md",
            "sql-injection-lab/evidence/image-01.png",
        ]
        assert archive.read("sql-injection-lab/evidence/image-01.png") == PNG
        assert all(not name.startswith("/") and ".." not in name.split("/") for name in archive.namelist())


async def test_export_rejects_foreign_evidence_and_detects_sensitive_content(client: httpx.AsyncClient) -> None:
    first_lab = await prepared_lab(client)
    second_platform = await create_platform(client, "Other platform")
    second_lab = await create_lab(client, second_platform["id"], title="Other lab")
    foreign = (await client.post(f"/api/labs/{second_lab['id']}/evidences", files={"files": ("foreign.png", PNG, "image/png")})).json()[0]
    generated = await client.post(f"/api/labs/{first_lab['id']}/report/generate", json={})
    sensitive = generated.json()["markdown"] + "\npassword=super-secret-value\n"
    saved = await client.put(f"/api/labs/{first_lab['id']}/report", json={"markdown": sensitive})
    assert "possível senha" in saved.json()["sensitive_warnings"]
    response = await client.post(
        f"/api/labs/{first_lab['id']}/report/export",
        json={"evidence_ids": [foreign["id"]], "sensitive_reviewed": True},
    )
    assert response.status_code == 422


async def test_export_enforces_size_limit_and_blocks_external_images(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    lab = await prepared_lab(client)
    await client.post(f"/api/labs/{lab['id']}/report/generate", json={})
    external = "# Manual\n\n![fora](https://example.invalid/image.png)\n"
    await client.put(f"/api/labs/{lab['id']}/report", json={"markdown": external})
    blocked = await client.post(
        f"/api/labs/{lab['id']}/report/export",
        json={"evidence_ids": [], "sensitive_reviewed": True},
    )
    assert blocked.status_code == 422

    safe = "# Manual\n"
    await client.put(f"/api/labs/{lab['id']}/report", json={"markdown": safe})
    monkeypatch.setattr(settings, "report_export_max_size", 2)
    too_large = await client.post(
        f"/api/labs/{lab['id']}/report/export",
        json={"evidence_ids": [], "sensitive_reviewed": True},
    )
    assert too_large.status_code == 413


async def test_export_blocks_active_html_and_generated_metadata_injection(
    client: httpx.AsyncClient,
) -> None:
    lab = await prepared_lab(client)
    uploaded = await client.post(
        f"/api/labs/{lab['id']}/evidences",
        files={"files": ("proof.png", PNG, "image/png")},
    )
    evidence = uploaded.json()[0]
    await client.patch(
        f"/api/labs/{lab['id']}/evidences/{evidence['id']}",
        json={
            "description": "caption\n![external](https://attacker.example/a.png)",
            "step_label": "step\n<script>alert(1)</script>",
        },
    )
    generated = await client.post(f"/api/labs/{lab['id']}/report/generate", json={})
    markdown = generated.json()["markdown"]
    assert "caption \\!\\[external\\]" in markdown
    assert "https://attacker.example/a.png" not in markdown
    assert "<script>" not in markdown

    await client.put(
        f"/api/labs/{lab['id']}/report",
        json={"markdown": "# Manual\n\n<img src=x onerror=alert(1)>"},
    )
    blocked = await client.post(
        f"/api/labs/{lab['id']}/report/export",
        json={"evidence_ids": [], "sensitive_reviewed": True},
    )
    assert blocked.status_code == 422
