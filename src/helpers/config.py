from pathlib import Path
from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.constants import MessageTemplate
from src.llm.model_catalog import (
    DEFAULT_CHAT_MODEL,
    DEFAULT_EMBEDDING_MODEL,
)
from src.vector_db.VectorDBModels import VectorCollectionConfig


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

    # Vector database selection. Each collection has its own vector space and
    # therefore its own dimension. Connection credentials stay provider-specific.
    vector_db_provider: str = Field(default="qdrant", min_length=1)
    vector_db_collections: list[VectorCollectionConfig] = Field(
        default_factory=list
    )
    vector_db_collection: str | None = Field(
        default=None,
        description=(
            "Collection used for indexing and search. Defaults to the "
            "first configured collection."
        ),
    )

    @property
    def active_vector_collection_name(self) -> str:
        if self.vector_db_collection and self.vector_db_collection.strip():
            return self.vector_db_collection.strip()

        if not self.vector_db_collections:
            return ""

        return self.vector_db_collections[0].name

    @model_validator(mode="after")
    def validate_active_vector_collection(self) -> "Settings":
        configured_names = {
            collection.name
            for collection in self.vector_db_collections
        }
        active_name = self.active_vector_collection_name

        if not configured_names and not active_name:
            return self

        if active_name not in configured_names:
            raise ValueError(
                MessageTemplate.VECTOR_DB_COLLECTION_NOT_CONFIGURED.format(
                    collection_name=active_name,
                )
            )

        return self

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
