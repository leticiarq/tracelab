from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    return tmp_path / "tracelab-test.db"


@pytest.fixture
def test_session_factory(database_path: Path) -> Generator[sessionmaker[Session], None, None]:
    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    yield factory
    engine.dispose()


@pytest.fixture
async def client(test_session_factory: sessionmaker[Session]) -> AsyncGenerator[httpx.AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[Session, None]:
        db = test_session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def isolated_evidence_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    storage = tmp_path / "private-evidences"
    monkeypatch.setattr(settings, "evidence_storage_path", storage)
    monkeypatch.setattr(settings, "evidence_max_file_size", 1024)
    monkeypatch.setattr(settings, "evidence_max_files_per_upload", 3)
    monkeypatch.setattr(settings, "evidence_max_files_per_lab", 5)
    return storage
