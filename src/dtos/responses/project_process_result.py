from pydantic import BaseModel, Field

from .processed_asset import ProcessedAssetDTO


class ProjectProcessResultDTO(BaseModel):
    project_id: str
    total_assets: int = Field(ge=0)
    processed_assets: int = Field(ge=0)
    failed_assets: int = Field(ge=0)
    total_chunks: int = Field(ge=0)
    assets: list[ProcessedAssetDTO] = Field(default_factory=list)
