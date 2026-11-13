"""Shared types for LLM prompt templates."""

from dataclasses import dataclass
from enum import StrEnum

from src.enums import QuestionLanguage


class PromptType(StrEnum):
    """Application flows that need a provider-agnostic prompt."""

    RAG_ANSWER = "rag_answer"


@dataclass(frozen=True, slots=True)
class PromptTemplate:
    """A language-specific system instruction and user prompt template."""

    prompt_type: PromptType
    language: QuestionLanguage
    system_instruction: str
    user_instruction_template: str
