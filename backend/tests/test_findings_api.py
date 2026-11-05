import base64
import io
import zipfile

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models.evidence import Evidence
from app.models.finding import Finding

from .test_lab_management_api import create_lab, create_platform

pytestmark = pytest.mark.anyio
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


async def make_lab(client: httpx.AsyncClient, title: str) -> dict:
    platform = await create_platform(client, f"Platform {title}")
    return await create_lab(client, platform["id"], title=title, objective="Documentar o laboratório")


def finding_payload(title: str) -> dict[str, str]:
    return {
        "title": title,
        "category": "Web",
        "cwe_id": "CWE-89",
        "description": f"Descrição de {title}",
        "technical_details": "Parâmetro sem validação.",
        "reproduction_steps": "1. Enviar payload\n2. Observar resposta",
        "impact": "Acesso indevido.",
        "mitigation": "Usar consultas parametrizadas.",
        "status": "confirmed",
    }


async def test_zero_one_many_crud_reorder_persistence_and_isolation(
    client: httpx.AsyncClient, test_session_factory: sessionmaker[Session]
) -> None:
    lab = await make_lab(client, "Multi")
    other = await make_lab(client, "Other")
    assert (await client.get(f"/api/labs/{lab['id']}/findings")).json() == []

    created = []
    for title in ("SQL Injection", "XSS", "IDOR"):
        response = await client.post(f"/api/labs/{lab['id']}/findings", json=finding_payload(title))
        assert response.status_code == 201, response.text
        created.append(response.json())
    assert [item["display_order"] for item in created] == [0, 1, 2]
    assert len({item["slug"] for item in created}) == 3

    updated = await client.patch(
        f"/api/labs/{lab['id']}/findings/{created[0]['id']}",
        json={"title": "SQL Injection crítica", "cwe_id": "cwe-89"},
    )
    assert updated.status_code == 200
    assert updated.json()["cwe_id"] == "CWE-89"
    assert (await client.get(f"/api/labs/{other['id']}/findings/{created[0]['id']}")).status_code == 404
    assert (await client.patch(
        f"/api/labs/{other['id']}/findings/{created[0]['id']}", json={"impact": "alterado"}
    )).status_code == 404

    order = [created[2]["id"], created[0]["id"], created[1]["id"]]
    reordered = await client.patch(f"/api/labs/{lab['id']}/findings/order", json={"finding_ids": order})
    assert [item["id"] for item in reordered.json()] == order
    assert [item["display_order"] for item in reordered.json()] == [0, 1, 2]

    with test_session_factory() as session:
        persisted = list(session.scalars(select(Finding).where(Finding.lab_id == lab["id"])))
        assert len(persisted) == 3


async def test_evidence_association_cvss_report_export_and_safe_finding_delete(
    client: httpx.AsyncClient,
    test_session_factory: sessionmaker[Session],
    isolated_evidence_storage,
) -> None:
    lab = await make_lab(client, "Report multi")
    other = await make_lab(client, "Foreign")
    first = (await client.post(f"/api/labs/{lab['id']}/findings", json=finding_payload("SQL Injection"))).json()
    second = (await client.post(f"/api/labs/{lab['id']}/findings", json=finding_payload("XSS"))).json()
    foreign = (await client.post(f"/api/labs/{other['id']}/findings", json=finding_payload("Foreign"))).json()
    uploaded = (await client.post(
        f"/api/labs/{lab['id']}/evidences", files={"files": ("proof.png", PNG, "image/png")}
    )).json()[0]
    path = isolated_evidence_storage / uploaded["stored_filename"]

    invalid = await client.patch(
        f"/api/labs/{lab['id']}/evidences/{uploaded['id']}", json={"finding_id": foreign["id"]}
    )
    assert invalid.status_code == 422
    associated = await client.patch(
        f"/api/labs/{lab['id']}/evidences/{uploaded['id']}",
        json={"finding_id": first["id"], "description": "Prova do SQLi"},
    )
    assert associated.json()["finding_id"] == first["id"]
    assert len((await client.get(f"/api/labs/{lab['id']}/findings/{first['id']}/evidences")).json()) == 1

    cvss = await client.put(
        f"/api/labs/{lab['id']}/findings/{first['id']}/cvss",
        json={
            "version": "3.1", "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
            "score": 9.8, "severity": "Crítica", "justification": "Exploração remota sem autenticação.",
        },
    )
    assert cvss.status_code == 200
    assert cvss.json()["score"] == 9.8

    report = await client.post(f"/api/labs/{lab['id']}/report/generate", json={})
    markdown = report.json()["markdown"]
    assert "## 4. Resumo dos achados" in markdown
    assert "SQL Injection" in markdown and "XSS" in markdown
    assert "9.8 · Crítica" in markdown
    assert "![Prova do SQLi](evidence/image-01.png)" in markdown
    exported = await client.post(
        f"/api/labs/{lab['id']}/report/export",
        json={"evidence_ids": [uploaded["id"]], "sensitive_reviewed": True},
    )
    assert exported.status_code == 200
    with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
        assert any(name.endswith("README.md") for name in archive.namelist())
        assert any(name.endswith("evidence/image-01.png") for name in archive.namelist())

    assert (await client.delete(f"/api/labs/{lab['id']}/findings/{first['id']}")).status_code == 204
    assert path.exists()
    with test_session_factory() as session:
        evidence = session.get(Evidence, uploaded["id"])
        assert evidence is not None and evidence.finding_id is None
    assert (await client.patch(
        f"/api/labs/{lab['id']}/evidences/{uploaded['id']}", json={"finding_id": second["id"]}
    )).status_code == 200


async def test_single_finding_markdown_uses_simplified_structure(client: httpx.AsyncClient) -> None:
    lab = await make_lab(client, "Single")
    finding = await client.post(
        f"/api/labs/{lab['id']}/findings", json=finding_payload("Command Injection")
    )
    assert finding.status_code == 201
    report = await client.post(f"/api/labs/{lab['id']}/report/generate", json={})
    assert report.status_code == 200
    markdown = report.json()["markdown"]
    assert "## 4. Vulnerabilidade" in markdown
    assert "### Command Injection" in markdown
    assert "Resumo dos achados" not in markdown
    assert "## 5. Vulnerabilidades" not in markdown
    assert "CVSS" not in markdown
