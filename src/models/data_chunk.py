from typing import Annotated

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field
from pydantic import PlainSerializer, WithJsonSchema


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


class DataChunk(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )

    id: PyObjectId | None = Field(default=None, alias="_id")
    chunk_text: str = Field(..., min_length=1)
    chunk_metadata: dict
    chunk_order: int = Field(..., gt=0)
    chunk_project_id: PyObjectId