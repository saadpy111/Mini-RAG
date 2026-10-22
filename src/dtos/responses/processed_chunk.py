from typing import Any

from pydantic import BaseModel, Field


class ProcessedChunkDTO(BaseModel):
    page_content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
