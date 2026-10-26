from datetime import datetime, timezone
from typing import Annotated, Any

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


class Asset(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )

    id: PyObjectId | None = Field(default=None, alias="_id")
    asset_project_id: PyObjectId
    asset_type: str = Field(min_length=1)
    asset_name: str = Field(min_length=1)
    asset_size: int = Field(ge=0)
    asset_config: dict[str, Any] = Field(default_factory=dict)
    asset_pushed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )