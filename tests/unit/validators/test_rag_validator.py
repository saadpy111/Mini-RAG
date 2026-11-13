import pytest

from src.constants import ErrorCode
from src.helpers.result_pattern import ErrorType
from src.validators.rag_validator import (
    validate_rag_project_id,
    validate_rag_question,
)


@pytest.mark.parametrize("question", ["", "   ", "\n\t"])
def test_validate_rag_question_rejects_empty_values(question):
    result = validate_rag_question(question)

    assert result.is_success is False
    assert result.error.code == ErrorCode.EMPTY_RAG_QUESTION
    assert result.error.type is ErrorType.VALIDATION


def test_validate_rag_question_trims_whitespace():
    result = validate_rag_question("  What is RAG?  ")

    assert result.is_success is True
    assert result.value == "What is RAG?"


@pytest.mark.parametrize("project_id", ["", "   ", "\n"])
def test_validate_rag_project_id_rejects_empty_values(project_id):
    result = validate_rag_project_id(project_id)

    assert result.is_success is False
    assert result.error.code == ErrorCode.INVALID_PROJECT_ID
    assert result.error.type is ErrorType.VALIDATION


def test_validate_rag_project_id_trims_whitespace():
    result = validate_rag_project_id("  project-1  ")

    assert result.is_success is True
    assert result.value == "project-1"
