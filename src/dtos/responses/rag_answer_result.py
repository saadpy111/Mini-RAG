from pydantic import BaseModel, Field

from .vector_result import VectorSearchResultDTO
from src.enums import QuestionLanguage


class RAGAnswerResultDTO(BaseModel):
    project_id: str
    question: str
    answer: str
    language: QuestionLanguage
    model: str
    sources: list[VectorSearchResultDTO] = Field(default_factory=list)
