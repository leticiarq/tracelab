import json
from dataclasses import dataclass
from pathlib import Path

from app.core.config import Settings, settings


@dataclass(frozen=True)
class AIConfig:
    enabled: bool
    model: str
    timeout_seconds: float
    keep_alive: str
    base_url: str


class AIConfigRepository:
    """Stores user-editable AI preferences separately from environment defaults."""

    def __init__(self, app_settings: Settings = settings) -> None:
        self.settings = app_settings

    def load(self) -> AIConfig:
        defaults = self._defaults()
        path = self.settings.ai_config_path
        if not path.exists():
            return defaults
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return defaults
        return AIConfig(
            enabled=payload.get("enabled", defaults.enabled),
            model=payload.get("model", defaults.model),
            timeout_seconds=defaults.timeout_seconds,
            keep_alive=defaults.keep_alive,
            base_url=defaults.base_url,
        )

    def save(self, *, enabled: bool | None = None, model: str | None = None) -> AIConfig:
        current = self.load()
        updated = AIConfig(
            enabled=current.enabled if enabled is None else enabled,
            model=current.model if model is None else model,
            timeout_seconds=current.timeout_seconds,
            keep_alive=current.keep_alive,
            base_url=current.base_url,
        )
        path = self.settings.ai_config_path
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(f"{path.suffix}.tmp")
        temporary.write_text(
            json.dumps({"enabled": updated.enabled, "model": updated.model}, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
        return updated

    def _defaults(self) -> AIConfig:
        return AIConfig(
            enabled=self.settings.ai_enabled,
            model=self.settings.ollama_model,
            timeout_seconds=self.settings.ollama_timeout_seconds,
            keep_alive=self.settings.ollama_keep_alive,
            base_url=self.settings.ollama_base_url.rstrip("/"),
        )
