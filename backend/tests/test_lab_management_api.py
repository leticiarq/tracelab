from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.models.lab import Lab

pytestmark = pytest.mark.anyio


async def create_platform(
    client: httpx.AsyncClient, name: str = "Hack The Box"
) -> dict:
    response = await client.post(
        "/api/platforms",
        json={"name": name, "website_url": "https://example.com"},
    )
    assert response.status_code == 201
    return response.json()


async def create_category(
    client: httpx.AsyncClient, platform_id: int | None, name: str = "Web"
) -> dict:
    response = await client.post(
        "/api/categories", json={"name": name, "platform_id": platform_id}
    )
    assert response.status_code == 201
    return response.json()


async def create_lab(
    client: httpx.AsyncClient,
    platform_id: int,
    category_id: int | None = None,
    **overrides: object,
) -> dict:
    payload: dict[str, object] = {
        "title": "Lame Machine",
        "platform_id": platform_id,
        "category_id": category_id,
        "notes": "Initial enumeration notes",
    }
    payload.update(overrides)
    response = await client.post("/api/labs", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def test_platform_crud_and_collision_safe_slugs(client: httpx.AsyncClient) -> None:
    first = await create_platform(client)
    second = await create_platform(client, "Hack Thé Box")

    assert first["slug"] == "hack-the-box"
    assert second["slug"] == "hack-the-box-2"
    assert first["id"] != second["id"]

    updated = await client.patch(
        f"/api/platforms/{first['id']}",
        json={"name": "PortSwigger Academy", "website_url": "https://portswigger.net/web-security"},
    )
    assert updated.status_code == 200
    assert updated.json()["slug"] == "portswigger-academy"
    assert updated.json()["id"] == first["id"]

    fetched = await client.get(f"/api/platforms/{first['id']}")
    assert fetched.json()["name"] == "PortSwigger Academy"

    deleted = await client.delete(f"/api/platforms/{second['id']}")
    assert deleted.status_code == 204
    assert (await client.get(f"/api/platforms/{second['id']}")).status_code == 404


async def test_category_crud_relation_and_filter(client: httpx.AsyncClient) -> None:
    first_platform = await create_platform(client)
    second_platform = await create_platform(client, "TryHackMe")
    category = await create_category(client, first_platform["id"])
    await create_category(client, second_platform["id"], "Forensics")

    filtered = await client.get(
        "/api/categories", params={"platform_id": first_platform["id"]}
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["id"] == category["id"]

    updated = await client.patch(
        f"/api/categories/{category['id']}", json={"name": "Web Exploitation"}
    )
    assert updated.status_code == 200
    assert updated.json()["slug"] == "web-exploitation"

    assert (await client.delete(f"/api/categories/{category['id']}")).status_code == 204
    missing_platform = await client.post(
        "/api/categories", json={"name": "Cloud", "platform_id": 9999}
    )
    assert missing_platform.status_code == 404


async def test_lab_create_read_update_delete_and_report_fields(client: httpx.AsyncClient) -> None:
    platform = await create_platform(client)
    category = await create_category(client, platform["id"])
    lab = await create_lab(
        client,
        platform["id"],
        category["id"],
        source_url="https://example.com/labs/lame",
        difficulty="easy",
        objective="Obtain administrator access",
        vulnerability_description="Outdated network service",
        impact="Remote code execution",
        mitigation="Upgrade the service",
        learnings="Validate service versions early",
    )

    assert lab["status"] == "todo"
    assert lab["notes"] == "Initial enumeration notes"
    assert lab["solved_at"] is None
    assert (await client.get(f"/api/labs/{lab['id']}")).json()["objective"] == "Obtain administrator access"

    updated = await client.patch(
        f"/api/labs/{lab['id']}",
        json={"title": "Lame Completed", "status": "solved", "notes": "Root obtained"},
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["id"] == lab["id"]
    assert body["slug"] == "lame-completed"
    assert body["status"] == "solved"
    assert body["notes"] == "Root obtained"
    assert body["solved_at"] is not None

    assert (await client.delete(f"/api/labs/{lab['id']}")).status_code == 204
    assert (await client.get(f"/api/labs/{lab['id']}")).status_code == 404


async def test_lab_search_filters_and_pagination(client: httpx.AsyncClient) -> None:
    first_platform = await create_platform(client)
    second_platform = await create_platform(client, "TryHackMe")
    web = await create_category(client, first_platform["id"])
    await create_lab(client, first_platform["id"], web["id"], title="Lame Linux", status="solved")
    await create_lab(client, first_platform["id"], web["id"], title="Lame Windows")
    await create_lab(client, second_platform["id"], None, title="Blue Windows", status="solved")

    result = await client.get(
        "/api/labs",
        params={
            "search": "lame",
            "platform_id": first_platform["id"],
            "category_id": web["id"],
            "status": "solved",
            "page": 1,
            "page_size": 1,
        },
    )
    assert result.status_code == 200
    assert result.json()["total"] == 1
    assert result.json()["pages"] == 1
    assert result.json()["items"][0]["title"] == "Lame Linux"

    paged = await client.get("/api/labs", params={"page": 2, "page_size": 2})
    assert paged.json()["total"] == 3
    assert paged.json()["pages"] == 2
    assert len(paged.json()["items"]) == 1


async def test_invalid_inputs_and_unknown_records(client: httpx.AsyncClient) -> None:
    invalid_platform = await client.post(
        "/api/platforms", json={"name": " ", "website_url": "not-a-url"}
    )
    assert invalid_platform.status_code == 422

    platform = await create_platform(client)
    invalid_lab = await client.post(
        "/api/labs",
        json={"title": "Valid", "platform_id": platform["id"], "status": "unknown"},
    )
    assert invalid_lab.status_code == 422
    null_required_field = await client.patch(
        f"/api/platforms/{platform['id']}", json={"name": None}
    )
    assert null_required_field.status_code == 422
    assert (await client.get("/api/labs", params={"page_size": 101})).status_code == 422

    for path in ("platforms", "categories", "labs"):
        assert (await client.get(f"/api/{path}/9999")).status_code == 404
        assert (await client.delete(f"/api/{path}/9999")).status_code == 404


async def test_relations_are_validated_and_referenced_records_are_protected(
    client: httpx.AsyncClient,
) -> None:
    first_platform = await create_platform(client)
    second_platform = await create_platform(client, "TryHackMe")
    category = await create_category(client, first_platform["id"])

    mismatched = await client.post(
        "/api/labs",
        json={
            "title": "Wrong relation",
            "platform_id": second_platform["id"],
            "category_id": category["id"],
        },
    )
    assert mismatched.status_code == 422

    lab = await create_lab(client, first_platform["id"], category["id"])
    assert (await client.delete(f"/api/categories/{category['id']}")).status_code == 409
    assert (await client.delete(f"/api/platforms/{first_platform['id']}")).status_code == 409
    assert (
        await client.patch(
            f"/api/categories/{category['id']}", json={"platform_id": second_platform["id"]}
        )
    ).status_code == 409

    await client.delete(f"/api/labs/{lab['id']}")
    await client.delete(f"/api/categories/{category['id']}")
    assert (await client.delete(f"/api/platforms/{first_platform['id']}")).status_code == 204


async def test_data_persists_after_database_reopen(
    client: httpx.AsyncClient,
    database_path: Path,
    test_session_factory: sessionmaker[Session],
) -> None:
    platform = await create_platform(client)
    lab = await create_lab(client, platform["id"], notes="Persistent notes")

    test_session_factory.kw["bind"].dispose()
    reopened_engine = create_engine(f"sqlite:///{database_path}")
    with Session(reopened_engine) as session:
        persisted = session.scalar(select(Lab).where(Lab.id == lab["id"]))
        assert persisted is not None
        assert persisted.notes == "Persistent notes"
    reopened_engine.dispose()


async def test_openapi_contains_lab_management_endpoints(client: httpx.AsyncClient) -> None:
    schema = (await client.get("/openapi.json")).json()
    assert "/api/platforms" in schema["paths"]
    assert "/api/categories" in schema["paths"]
    assert "/api/labs" in schema["paths"]
    assert set(schema["paths"]["/api/labs"]) == {"get", "post"}
