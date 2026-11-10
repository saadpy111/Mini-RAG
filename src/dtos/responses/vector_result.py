from pydantic import BaseModel, Field


class VectorIndexResultDTO(BaseModel):
    project_id: str
    indexed_count: int = Field(ge=0)


class VectorSearchResultDTO(BaseModel):
    chunk_id: str
    project_id: str
    asset_id: str
    chunk_index: int = Field(ge=0)
    text: str
    score: float
