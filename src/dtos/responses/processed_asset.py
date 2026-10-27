from typing import Annotated

from bson import ObjectId
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    WithJsonSchema,
)


PyObjectId = Annotated[
    ObjectId,
    PlainSerializer(
        str,
        return_type=str,
        when_used="json",
    ),
    WithJsonSchema({
        "type": "string",
        "pattern": "^[0-9a-fA-F]{24}$",
    }),
]


class ProcessedAssetDTO(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )

    asset_id: PyObjectId | None = None
    file_id: str | None = None
    is_success: bool
    chunk_count: int = Field(default=0, ge=0)
    error_code: str | None = None
    error_message: str | None = None
