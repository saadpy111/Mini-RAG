from pathlib import Path
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.llm.model_catalog import (
    DEFAULT_CHAT_MODEL,
    DEFAULT_EMBEDDING_MODEL,
)


ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Mini-RAG"
    app_version: str = "0.1.0"
    mongodb_uri: str
    mongodb_database: str = "mini_rag"
    openai_api_key: SecretStr = SecretStr("")

    file_allowed_types: list[str] = Field(
        default_factory=lambda: [".pdf", ".txt", ".docx"]
    )
    file_max_size: int = Field(default=10, gt=0)
    file_default_chunk_size: int = Field(default=512000, gt=0)

    # LLM provider selection. Provider-specific credentials live with their
    # provider configuration.
    chat_provider: str = Field(default="openrouter", min_length=1)
    chat_model: str = Field(default=DEFAULT_CHAT_MODEL, min_length=1)
    embedding_provider: str = Field(default="openrouter", min_length=1)
    embedding_model: str = Field(default=DEFAULT_EMBEDDING_MODEL, min_length=1)

    # Shared LLM HTTP transport timeouts in seconds.
    llm_connect_timeout: float = Field(default=10.0, gt=0)
    llm_read_timeout: float = Field(default=60.0, gt=0)

    # Manual diagnostic endpoints (real provider calls), disabled by default.
    llm_test_endpoints_enabled: bool = False

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
