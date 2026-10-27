from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProjectProcessRequest(BaseModel):
    chunk_size: int = Field(default=100, gt=0)
    overlap_size: int = Field(default=20, ge=0)

    model_config = ConfigDict(str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_overlap_size(self) -> "ProjectProcessRequest":
        if self.overlap_size >= self.chunk_size:
            raise ValueError("overlap_size must be smaller than chunk_size.")
        return self
