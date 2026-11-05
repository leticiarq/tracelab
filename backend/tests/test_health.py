import httpx
import pytest

from app.main import app

pytestmark = pytest.mark.anyio

async def test_health_check() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_cors_allows_only_configured_frontend() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        allowed = await client.get("/health", headers={"Origin": "http://localhost:5173"})
        rejected = await client.get("/health", headers={"Origin": "http://example.com"})

    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in rejected.headers


async def test_rejects_cross_site_mutations_and_untrusted_hosts() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        cross_site = await client.post(
            "/api/platforms",
            headers={"Origin": "https://attacker.example"},
            json={"name": "Blocked", "website_url": "https://example.com"},
        )
        fetch_metadata = await client.post(
            "/api/platforms",
            headers={
                "Origin": "http://localhost:5173",
                "Sec-Fetch-Site": "cross-site",
            },
            json={"name": "Blocked", "website_url": "https://example.com"},
        )
        allowed = await client.post(
            "/api/platforms",
            headers={"Origin": "http://localhost:5173"},
            json={"name": "Allowed", "website_url": "https://example.com"},
        )
        untrusted_host = await client.get(
            "/health", headers={"Host": "attacker.example"}
        )

    assert cross_site.status_code == 403
    assert fetch_metadata.status_code == 403
    assert allowed.status_code == 201
    assert untrusted_host.status_code == 400
