"""OpenRouter-specific configuration."""

from dataclasses import dataclass
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
ROOT_DIR = Path(__file__).resolve().parents[4]


class OpenRouterSettings(BaseSettings):
    """Environment-backed OpenRouter credentials."""

    api_key: SecretStr = SecretStr("")

    model_config = SettingsConfigDict(
        env_prefix="OPENROUTER_",
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@dataclass(frozen=True)
class OpenRouterProviderConfig:
    """Configuration required by the OpenRouter adapters."""

    api_key: str
    base_url: str = OPENROUTER_BASE_URL

    @classmethod
    def from_environment(cls) -> "OpenRouterProviderConfig":
        settings = OpenRouterSettings()
        return cls(api_key=settings.api_key.get_secret_value())
