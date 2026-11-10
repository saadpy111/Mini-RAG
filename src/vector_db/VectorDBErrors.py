"""Application-level errors for the vector database layer."""

from src.constants import ErrorCode, ErrorMessage, MessageTemplate
from src.helpers.result_pattern import ErrorType, ResultError


def _error(
    code: ErrorCode,
    message: str,
    error_type: ErrorType = ErrorType.INTERNAL,
) -> ResultError:
    return ResultError(
        code=code,
        message=message,
        type=error_type,
    )


def unsupported_provider_error() -> ResultError:
    return _error(
        ErrorCode.VECTOR_DB_PROVIDER_UNSUPPORTED,
        ErrorMessage.VECTOR_DB_PROVIDER_UNSUPPORTED,
        ErrorType.VALIDATION,
    )


def invalid_configuration_error() -> ResultError:
    return _error(
        ErrorCode.VECTOR_DB_CONFIGURATION_INVALID,
        ErrorMessage.VECTOR_DB_CONFIGURATION_INVALID,
        ErrorType.VALIDATION,
    )


def duplicate_collection_error(collection_name: str) -> ResultError:
    return _error(
        ErrorCode.VECTOR_DB_CONFIGURATION_INVALID,
        MessageTemplate.VECTOR_DB_DUPLICATE_COLLECTION.format(
            collection_name=collection_name,
        ),
        ErrorType.VALIDATION,
    )


def connection_failed_error() -> ResultError:
    return _error(
        ErrorCode.VECTOR_DB_CONNECTION_FAILED,
        ErrorMessage.VECTOR_DB_CONNECTION_FAILED,
        ErrorType.SERVICE_UNAVAILABLE,
    )


def collection_initialization_error() -> ResultError:
    return _error(
        ErrorCode.VECTOR_DB_COLLECTION_INITIALIZATION_FAILED,
        ErrorMessage.VECTOR_DB_COLLECTION_INITIALIZATION_FAILED,
        ErrorType.INTERNAL,
    )


def collection_not_configured_error(collection_name: str) -> ResultError:
    return _error(
        ErrorCode.VECTOR_DB_COLLECTION_NOT_CONFIGURED,
        MessageTemplate.VECTOR_DB_COLLECTION_NOT_CONFIGURED.format(
            collection_name=collection_name,
        ),
        ErrorType.VALIDATION,
    )


def collection_dimension_mismatch_error(
    collection_name: str,
    expected: int,
    actual: int,
) -> ResultError:
    return _error(
        ErrorCode.VECTOR_DB_COLLECTION_MISMATCH,
        MessageTemplate.VECTOR_DB_COLLECTION_DIMENSION_MISMATCH.format(
            collection_name=collection_name,
            expected=expected,
            actual=actual,
        ),
        ErrorType.VALIDATION,
    )


def collection_distance_mismatch_error(
    collection_name: str,
    expected: str,
    actual: str,
) -> ResultError:
    return _error(
        ErrorCode.VECTOR_DB_COLLECTION_MISMATCH,
        MessageTemplate.VECTOR_DB_COLLECTION_DISTANCE_MISMATCH.format(
            collection_name=collection_name,
            expected=expected,
            actual=actual,
        ),
        ErrorType.VALIDATION,
    )


def collection_layout_unsupported_error(collection_name: str) -> ResultError:
    return _error(
        ErrorCode.VECTOR_DB_COLLECTION_MISMATCH,
        MessageTemplate.VECTOR_DB_COLLECTION_LAYOUT_UNSUPPORTED.format(
            collection_name=collection_name,
        ),
        ErrorType.VALIDATION,
    )


def invalid_vector_id_error(vector_id: str) -> ResultError:
    return _error(
        ErrorCode.VECTOR_DB_INVALID_VECTOR_ID,
        MessageTemplate.VECTOR_DB_INVALID_VECTOR_ID.format(
            vector_id=vector_id,
        ),
        ErrorType.VALIDATION,
    )


def invalid_vector_dimension_error(
    collection_name: str,
    expected: int,
    actual: int,
) -> ResultError:
    return _error(
        ErrorCode.VECTOR_DB_INVALID_VECTOR_DIMENSION,
        MessageTemplate.VECTOR_DB_INVALID_VECTOR_DIMENSION.format(
            collection_name=collection_name,
            expected=expected,
            actual=actual,
        ),
        ErrorType.VALIDATION,
    )


def invalid_payload_error() -> ResultError:
    return _error(
        ErrorCode.VECTOR_DB_INVALID_PAYLOAD,
        ErrorMessage.VECTOR_DB_INVALID_PAYLOAD,
        ErrorType.VALIDATION,
    )


def invalid_project_filter_error() -> ResultError:
    return _error(
        ErrorCode.VECTOR_DB_INVALID_PROJECT_FILTER,
        ErrorMessage.VECTOR_DB_INVALID_PROJECT_FILTER,
        ErrorType.VALIDATION,
    )


def invalid_search_limit_error() -> ResultError:
    return _error(
        ErrorCode.VECTOR_DB_INVALID_SEARCH_LIMIT,
        ErrorMessage.VECTOR_DB_INVALID_SEARCH_LIMIT,
        ErrorType.VALIDATION,
    )


def upsert_failed_error() -> ResultError:
    return _error(
        ErrorCode.VECTOR_DB_UPSERT_FAILED,
        ErrorMessage.VECTOR_DB_UPSERT_FAILED,
    )


def search_failed_error() -> ResultError:
    return _error(
        ErrorCode.VECTOR_DB_SEARCH_FAILED,
        ErrorMessage.VECTOR_DB_SEARCH_FAILED,
    )


def delete_failed_error() -> ResultError:
    return _error(
        ErrorCode.VECTOR_DB_DELETE_FAILED,
        ErrorMessage.VECTOR_DB_DELETE_FAILED,
    )


def project_vector_lookup_failed_error() -> ResultError:
    return _error(
        ErrorCode.VECTOR_DB_PROJECT_VECTOR_LOOKUP_FAILED,
        ErrorMessage.VECTOR_DB_PROJECT_VECTOR_LOOKUP_FAILED,
    )
