from pathlib import Path
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
