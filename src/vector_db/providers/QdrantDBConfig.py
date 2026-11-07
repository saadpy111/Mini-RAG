"""Qdrant-specific connection configuration."""

from dataclasses import dataclass, field
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]


class QdrantSettings(BaseSettings):
    """Environment-backed Qdrant connection settings."""

    url: str = Field(default="http://localhost:6333", min_length=1)
    api_key: SecretStr = SecretStr("")
    timeout: int = Field(default=30, gt=0)

    model_config = SettingsConfigDict(
        env_prefix="QDRANT_",
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@dataclass(frozen=True)
class QdrantDBConfig:
    """Connection details required by the Qdrant adapter."""

    url: str
    api_key: str = field(repr=False)
    timeout: int = 30

    @classmethod
    def from_environment(cls) -> "QdrantDBConfig":
        settings = QdrantSettings()
        return cls(
            url=settings.url,
            api_key=settings.api_key.get_secret_value(),
            timeout=settings.timeout,
        )
