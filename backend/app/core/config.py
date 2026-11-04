from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_prefix="TRACELAB_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "TraceLab API"
    app_env: str = "development"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    database_url: str = "sqlite:///./data/tracelab.db"
    cors_origins: list[str] = ["http://localhost:5173"]
    evidence_storage_path: Path = PROJECT_ROOT / "backend" / "data" / "evidences"
    evidence_max_file_size: int = 10 * 1024 * 1024
    evidence_max_files_per_upload: int = 10
    evidence_max_files_per_lab: int = 100
    report_export_max_size: int = 50 * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
