"""Shared standardized errors for the LLM integration."""

from src.constants import ErrorCode, ErrorMessage
from src.helpers.result_pattern import ErrorType, ResultError


def make_error(
    code: ErrorCode,
    message: ErrorMessage,
    error_type: ErrorType = ErrorType.INTERNAL,
) -> ResultError:
    return ResultError(code=code, message=message, type=error_type)


def unsupported_provider_error() -> ResultError:
    return make_error(
        ErrorCode.LLM_PROVIDER_UNSUPPORTED,
        ErrorMessage.LLM_PROVIDER_UNSUPPORTED,
        ErrorType.VALIDATION,
    )


def unapproved_model_error() -> ResultError:
    return make_error(
        ErrorCode.LLM_MODEL_NOT_APPROVED,
        ErrorMessage.LLM_MODEL_NOT_APPROVED,
        ErrorType.VALIDATION,
    )


def missing_api_key_error() -> ResultError:
    return make_error(
        ErrorCode.LLM_API_KEY_MISSING,
        ErrorMessage.LLM_API_KEY_MISSING,
    )


def invalid_response_error() -> ResultError:
    return make_error(
        ErrorCode.LLM_INVALID_RESPONSE,
        ErrorMessage.LLM_INVALID_RESPONSE,
    )


def invalid_chat_messages_error() -> ResultError:
    return make_error(
        ErrorCode.INVALID_CHAT_MESSAGES,
        ErrorMessage.INVALID_CHAT_MESSAGES,
        ErrorType.VALIDATION,
    )


def empty_embedding_input_error() -> ResultError:
    return make_error(
        ErrorCode.EMPTY_EMBEDDING_INPUT,
        ErrorMessage.EMPTY_EMBEDDING_INPUT,
        ErrorType.VALIDATION,
    )
