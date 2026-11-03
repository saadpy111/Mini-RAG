from pydantic import BaseModel, Field


class ChatTestResultDTO(BaseModel):
    model: str
    content: str


class EmbeddingTestResultDTO(BaseModel):
    model: str
    dimensions: int = Field(gt=0)
    embedding: list[float]
