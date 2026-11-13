from enum import StrEnum


class QuestionLanguage(StrEnum):
    """Languages supported by the RAG prompt templates."""

    ARABIC = "ar"
    ENGLISH = "en"
