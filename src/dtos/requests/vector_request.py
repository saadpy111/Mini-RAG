from pydantic import BaseModel, ConfigDict, Field


class VectorIndexRequest(BaseModel):
    do_reset: bool = False


class VectorSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    limit: int = Field(default=5, gt=0, le=100)

    model_config = ConfigDict(str_strip_whitespace=True)
