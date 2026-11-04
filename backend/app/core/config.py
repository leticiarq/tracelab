from functools import lru_cache
import ipaddress
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import field_validator
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
    ai_enabled: bool = True
    ai_config_path: Path = PROJECT_ROOT / "backend" / "data" / "ai-settings.json"
    ai_max_images: int = 4
    ai_max_image_bytes: int = 10 * 1024 * 1024
    ai_max_image_dimension: int = 1600
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3-vl:2b"
    ollama_timeout_seconds: float = 120.0
    ollama_keep_alive: str = "5m"

    @field_validator("ollama_base_url")
    @classmethod
    def ollama_must_be_local(cls, value: str) -> str:
        parsed = urlsplit(value)
        host = parsed.hostname
        is_loopback = host == "localhost"
        if host and not is_loopback:
            try:
                is_loopback = ipaddress.ip_address(host).is_loopback
            except ValueError:
                is_loopback = False
        if (
            parsed.scheme not in {"http", "https"}
            or not is_loopback
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("O Ollama deve usar uma URL local em localhost ou endereço de loopback.")
        return value.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
