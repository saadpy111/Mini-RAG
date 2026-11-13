import pytest

from src.constants import ErrorCode
from src.enums import QuestionLanguage
from src.helpers.result_pattern import ErrorType
from src.llm.templates import PROMPT_TEMPLATES, get_prompt_template
from src.llm.templates.types import PromptType


def test_registry_has_rag_answer_template_for_every_language():
    for language in QuestionLanguage:
        assert (PromptType.RAG_ANSWER, language) in PROMPT_TEMPLATES


@pytest.mark.parametrize(
    "language",
    [QuestionLanguage.ENGLISH, QuestionLanguage.ARABIC],
)
def test_get_prompt_template_selects_the_requested_language(language):
    result = get_prompt_template(
        language,
        PromptType.RAG_ANSWER,
    )

    assert result.is_success is True
    assert result.value.language is language
    assert result.value.prompt_type is PromptType.RAG_ANSWER


def test_get_prompt_template_fails_for_missing_template():
    result = get_prompt_template("fr")

    assert result.is_success is False
    assert result.error.code == ErrorCode.PROMPT_TEMPLATE_NOT_FOUND
    assert result.error.type is ErrorType.INTERNAL
