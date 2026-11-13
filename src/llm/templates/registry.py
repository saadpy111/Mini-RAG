"""Registry of prompt templates keyed by prompt type and language."""

from collections.abc import Mapping
from types import MappingProxyType

from src.constants import ErrorCode, ErrorMessage
from src.enums import QuestionLanguage
from src.helpers.result_pattern import ErrorType, Result, ResultError
from src.llm.templates.arabic import ARABIC_RAG_ANSWER_TEMPLATE
from src.llm.templates.english import ENGLISH_RAG_ANSWER_TEMPLATE
from src.llm.templates.types import PromptTemplate, PromptType


PROMPT_TEMPLATES: Mapping[
    tuple[PromptType, QuestionLanguage],
    PromptTemplate,
] = MappingProxyType(
    {
        (
            PromptType.RAG_ANSWER,
            QuestionLanguage.ENGLISH,
        ): ENGLISH_RAG_ANSWER_TEMPLATE,
        (
            PromptType.RAG_ANSWER,
            QuestionLanguage.ARABIC,
        ): ARABIC_RAG_ANSWER_TEMPLATE,
    }
)


def get_prompt_template(
    language: QuestionLanguage,
    prompt_type: PromptType = PromptType.RAG_ANSWER,
) -> Result[PromptTemplate]:
    """Return the template registered for ``prompt_type`` and ``language``."""

    template = PROMPT_TEMPLATES.get((prompt_type, language))

    if template is None:
        return Result.failure(
            ResultError(
                code=ErrorCode.PROMPT_TEMPLATE_NOT_FOUND,
                message=ErrorMessage.PROMPT_TEMPLATE_NOT_FOUND,
                type=ErrorType.INTERNAL,
            )
        )

    return Result.success(template)
