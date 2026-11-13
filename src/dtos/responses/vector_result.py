from pydantic import BaseModel, Field

from src.vector_db.VectorDBModels import VectorSearchResult


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

    @classmethod
    def from_search_result(
        cls,
        result: VectorSearchResult,
    ) -> "VectorSearchResultDTO":
        metadata = result.metadata

        return cls(
            chunk_id=str(metadata.get("chunk_id") or result.vector_id),
            project_id=str(metadata.get("project_id") or ""),
            asset_id=str(metadata.get("asset_id") or ""),
            chunk_index=int(metadata.get("chunk_index") or 0),
            text=str(metadata.get("text") or ""),
            score=result.score,
        )
