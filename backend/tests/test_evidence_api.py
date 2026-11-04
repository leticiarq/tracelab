import base64
import hashlib
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.models.evidence import Evidence

from .test_lab_management_api import create_lab, create_platform

pytestmark = pytest.mark.anyio

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)
JPEG = b"\xff\xd8\xff\xe0" + b"safe-jpeg-payload" + b"\xff\xd9"
WEBP = b"RIFF" + (12).to_bytes(4, "little") + b"WEBPVP8 " + (0).to_bytes(4, "little")


async def lab_id(client: httpx.AsyncClient, title: str = "Evidence lab") -> int:
    platform = await create_platform(client, f"Platform {title}")
    lab = await create_lab(client, platform["id"], title=title)
    return lab["id"]


async def test_multiple_valid_uploads_metadata_content_and_persistence(
    client: httpx.AsyncClient,
    database_path: Path,
    test_session_factory: sessionmaker[Session],
    isolated_evidence_storage: Path,
) -> None:
    target_lab = await lab_id(client)
    response = await client.post(
        f"/api/labs/{target_lab}/evidences",
        files=[
            ("files", ("first.png", PNG, "image/png")),
            ("files", ("request.http", b"GET /admin HTTP/1.1\r\nHost: target\r\n", "text/plain")),
            ("files", ("notes.txt", b"Response: access granted", "text/html")),
        ],
    )
    assert response.status_code == 201, response.text
    uploaded = response.json()
    assert [item["display_order"] for item in uploaded] == [0, 1, 2]
    assert uploaded[0]["sha256"] == hashlib.sha256(PNG).hexdigest()
    assert uploaded[1]["mime_type"] == "message/http"
    assert uploaded[2]["mime_type"] == "text/plain"
    assert all(".." not in item["stored_filename"] for item in uploaded)
    assert {path.name for path in isolated_evidence_storage.iterdir()} == {
        item["stored_filename"] for item in uploaded
    }

    image = await client.get(
        f"/api/labs/{target_lab}/evidences/{uploaded[0]['id']}/content"
    )
    assert image.content == PNG
    assert image.headers["content-type"] == "image/png"
    assert image.headers["x-content-type-options"] == "nosniff"
    text = await client.get(
        f"/api/labs/{target_lab}/evidences/{uploaded[2]['id']}/content"
    )
    assert text.text == "Response: access granted"
    assert text.headers["content-type"].startswith("text/plain")

    download = await client.get(
        f"/api/labs/{target_lab}/evidences/{uploaded[0]['id']}/download"
    )
    assert "attachment" in download.headers["content-disposition"]
    assert download.content == PNG

    test_session_factory.kw["bind"].dispose()
    reopened_engine = create_engine(f"sqlite:///{database_path}")
    with Session(reopened_engine) as session:
        persisted = list(
            session.scalars(
                select(Evidence)
                .where(Evidence.lab_id == target_lab)
                .order_by(Evidence.display_order)
            )
        )
        assert len(persisted) == 3
        assert isolated_evidence_storage.joinpath(persisted[0].stored_filename).read_bytes() == PNG
    reopened_engine.dispose()


@pytest.mark.parametrize(
    ("filename", "content"),
    [
        ("payload.exe", b"MZ"),
        ("fake.png", b"not an image"),
        ("binary.txt", b"safe\x00unsafe"),
        ("latin.txt", b"\xff\xfe"),
        ("../escape.txt", b"no"),
        ("folder\\escape.txt", b"no"),
        ("empty.txt", b""),
    ],
)
async def test_rejects_invalid_uploads(
    client: httpx.AsyncClient,
    filename: str,
    content: bytes,
    isolated_evidence_storage: Path,
) -> None:
    target_lab = await lab_id(client, filename.replace("/", "-").replace("\\", "-"))
    response = await client.post(
        f"/api/labs/{target_lab}/evidences",
        files={"files": (filename, content, "application/octet-stream")},
    )
    assert response.status_code == 422
    assert not isolated_evidence_storage.exists() or not list(isolated_evidence_storage.iterdir())


async def test_enforces_file_batch_and_lab_limits(
    client: httpx.AsyncClient, isolated_evidence_storage: Path
) -> None:
    target_lab = await lab_id(client)
    too_large = await client.post(
        f"/api/labs/{target_lab}/evidences",
        files={"files": ("large.txt", b"x" * 1025, "text/plain")},
    )
    assert too_large.status_code == 413
    too_many = await client.post(
        f"/api/labs/{target_lab}/evidences",
        files=[("files", (f"{index}.txt", str(index).encode(), "text/plain")) for index in range(4)],
    )
    assert too_many.status_code == 422
    assert not isolated_evidence_storage.exists() or not list(isolated_evidence_storage.iterdir())


async def test_duplicate_is_atomic_and_uses_sha256(
    client: httpx.AsyncClient, isolated_evidence_storage: Path
) -> None:
    target_lab = await lab_id(client)
    duplicate_batch = await client.post(
        f"/api/labs/{target_lab}/evidences",
        files=[
            ("files", ("one.txt", b"same", "text/plain")),
            ("files", ("two.http", b"same", "text/plain")),
        ],
    )
    assert duplicate_batch.status_code == 409
    assert not isolated_evidence_storage.exists() or not list(isolated_evidence_storage.iterdir())

    first = await client.post(
        f"/api/labs/{target_lab}/evidences",
        files={"files": ("one.txt", b"same", "text/plain")},
    )
    assert first.status_code == 201
    duplicate = await client.post(
        f"/api/labs/{target_lab}/evidences",
        files={"files": ("renamed.txt", b"same", "text/plain")},
    )
    assert duplicate.status_code == 409
    assert len(list(isolated_evidence_storage.iterdir())) == 1


async def test_update_reorder_delete_and_lab_isolation(
    client: httpx.AsyncClient, isolated_evidence_storage: Path
) -> None:
    first_lab = await lab_id(client, "First")
    second_lab = await lab_id(client, "Second")
    uploaded = (
        await client.post(
            f"/api/labs/{first_lab}/evidences",
            files=[
                ("files", ("shot.jpg", JPEG, "image/jpeg")),
                ("files", ("shot.webp", WEBP, "image/webp")),
            ],
        )
    ).json()
    first_id, second_id = uploaded[0]["id"], uploaded[1]["id"]
    updated = await client.patch(
        f"/api/labs/{first_lab}/evidences/{first_id}",
        json={"description": "  Login vulnerável  ", "step_label": "  Exploração  "},
    )
    assert updated.json()["description"] == "Login vulnerável"
    assert updated.json()["step_label"] == "Exploração"

    reordered = await client.patch(
        f"/api/labs/{first_lab}/evidences/order",
        json={"evidence_ids": [second_id, first_id]},
    )
    assert [item["id"] for item in reordered.json()] == [second_id, first_id]
    assert [item["display_order"] for item in reordered.json()] == [0, 1]
    assert (
        await client.get(f"/api/labs/{second_lab}/evidences/{first_id}/content")
    ).status_code == 404

    deleted_name = uploaded[0]["stored_filename"]
    assert (
        await client.delete(f"/api/labs/{first_lab}/evidences/{first_id}")
    ).status_code == 204
    assert not isolated_evidence_storage.joinpath(deleted_name).exists()
    remaining = (await client.get(f"/api/labs/{first_lab}/evidences")).json()
    assert remaining[0]["display_order"] == 0

    remaining_name = remaining[0]["stored_filename"]
    assert (await client.delete(f"/api/labs/{first_lab}")).status_code == 204
    assert not isolated_evidence_storage.joinpath(remaining_name).exists()


async def test_rejects_incomplete_or_cross_lab_reorder(client: httpx.AsyncClient) -> None:
    target_lab = await lab_id(client)
    uploaded = (
        await client.post(
            f"/api/labs/{target_lab}/evidences",
            files=[
                ("files", ("one.txt", b"one", "text/plain")),
                ("files", ("two.txt", b"two", "text/plain")),
            ],
        )
    ).json()
    response = await client.patch(
        f"/api/labs/{target_lab}/evidences/order",
        json={"evidence_ids": [uploaded[0]["id"]]},
    )
    assert response.status_code == 422
