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


class ProcessedFileDTO(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )

    project_id: str
    asset_id: PyObjectId
    file_id: str
    is_success: bool
    total_chunks: int = Field(ge=0)
