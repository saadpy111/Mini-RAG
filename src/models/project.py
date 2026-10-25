
from typing import Annotated

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, PlainSerializer,validator,WithJsonSchema


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


class Project(BaseModel):
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
    )

    id: PyObjectId | None = Field(default=None, alias="_id")
    project_id: str = Field(..., min_length=1)


    # @validator('project_id')
    # def validate_project_id(cls, value):
    #     if not value.isalnum():
    #         raise ValueError('project_id must be alphanumeric')
        
    #     return value

