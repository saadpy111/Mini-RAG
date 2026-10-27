from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.constants import ErrorMessage


class ProcessRequest(BaseModel):
    file_id: str = Field(
        min_length=1,
        description="Identifier returned by the upload endpoint (without extension).",
    )
    chunk_size: int = Field(default=100, gt=0)
    overlap_size: int = Field(default=20, ge=0)
    do_reset: bool = Field(
        default=False,
        description="Reserved for future reset support. Reset is not implemented.",
    )

    model_config = ConfigDict(str_strip_whitespace=True)

    @model_validator(mode="after")
    def validate_overlap_size(self) -> "ProcessRequest":
        if self.overlap_size >= self.chunk_size:
            raise ValueError(ErrorMessage.INVALID_CHUNK_CONFIGURATION)
        return self
