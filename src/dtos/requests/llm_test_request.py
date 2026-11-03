from pydantic import BaseModel, ConfigDict, Field


class ChatTestRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    model: str = Field(min_length=1)

    model_config = ConfigDict(str_strip_whitespace=True)


class EmbeddingTestRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    model: str = Field(min_length=1)

    model_config = ConfigDict(str_strip_whitespace=True)
