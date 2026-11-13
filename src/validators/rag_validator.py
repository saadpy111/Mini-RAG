"""Validation for RAG answer requests."""

from src.constants import ErrorCode, ErrorMessage
from src.helpers.result_pattern import ErrorType, Result, ResultError


def validate_rag_question(question: str) -> Result[str]:
    if not isinstance(question, str) or not question.strip():
        return Result.failure(
            ResultError(
                code=ErrorCode.EMPTY_RAG_QUESTION,
                message=ErrorMessage.EMPTY_RAG_QUESTION,
                type=ErrorType.VALIDATION,
            )
        )

    return Result.success(question.strip())


def validate_rag_project_id(project_id: str) -> Result[str]:
    if not isinstance(project_id, str) or not project_id.strip():
        return Result.failure(
            ResultError(
                code=ErrorCode.INVALID_PROJECT_ID,
                message=ErrorMessage.INVALID_PROJECT_ID,
                type=ErrorType.VALIDATION,
            )
        )

    return Result.success(project_id.strip())
