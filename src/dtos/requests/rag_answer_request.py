from pydantic import BaseModel, ConfigDict, Field


class RAGAnswerRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)

    model_config = ConfigDict(str_strip_whitespace=True)
