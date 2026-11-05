from pathlib import Path

from app.core.config import BACKEND_ROOT, PROJECT_ROOT, Settings


def test_relative_data_paths_are_independent_from_working_directory() -> None:
    configured = Settings(
        _env_file=None,
        database_url="sqlite:///./data/custom.db",
        evidence_storage_path=Path("backend/data/custom-evidence"),
    )

    assert configured.database_url == f"sqlite:///{BACKEND_ROOT / 'data/custom.db'}"
    assert configured.evidence_storage_path == PROJECT_ROOT / "backend/data/custom-evidence"
