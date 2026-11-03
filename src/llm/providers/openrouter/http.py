"""OpenRouter HTTP request helpers and error translation."""

import logging
from typing import Any

import httpx

from src.constants import ErrorCode, ErrorMessage
from src.helpers.result_pattern import ErrorType, Result, ResultError
from src.llm.errors import (
    invalid_response_error,
    make_error,
    missing_api_key_error,
)

CHAT_COMPLETIONS_PATH = "/chat/completions"
EMBEDDINGS_PATH = "/embeddings"

logger = logging.getLogger(__name__)


def endpoint_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}{path}"


def authorization_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def map_http_status(status_code: int) -> ResultError:
    if status_code == 401:
        return make_error(
            ErrorCode.LLM_AUTH_FAILED,
            ErrorMessage.LLM_AUTH_FAILED,
        )

    if status_code == 429:
        return make_error(
            ErrorCode.LLM_RATE_LIMITED,
            ErrorMessage.LLM_RATE_LIMITED,
            ErrorType.SERVICE_UNAVAILABLE,
        )

    if status_code in {408, 504}:
        return make_error(
            ErrorCode.LLM_TIMEOUT,
            ErrorMessage.LLM_TIMEOUT,
            ErrorType.SERVICE_UNAVAILABLE,
        )

    return make_error(
        ErrorCode.LLM_PROVIDER_ERROR,
        ErrorMessage.LLM_PROVIDER_ERROR,
    )


def map_transport_error(exc: Exception) -> ResultError:
    if isinstance(exc, httpx.TimeoutException):
        return make_error(
            ErrorCode.LLM_TIMEOUT,
            ErrorMessage.LLM_TIMEOUT,
            ErrorType.SERVICE_UNAVAILABLE,
        )

    return make_error(
        ErrorCode.LLM_PROVIDER_ERROR,
        ErrorMessage.LLM_PROVIDER_ERROR,
    )


async def post_json(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    path: str,
    payload: dict[str, Any],
    api_key: str,
    operation: str,
) -> Result[Any]:
    """POST ``payload`` to OpenRouter and return the decoded JSON body."""

    if not api_key:
        return Result.failure(missing_api_key_error())

    try:
        response = await client.post(
            endpoint_url(base_url, path),
            json=payload,
            headers=authorization_headers(api_key),
        )
    except httpx.HTTPError as exc:
        logger.warning(
            "%s request failed: %s",
            operation,
            type(exc).__name__,
        )
        return Result.failure(map_transport_error(exc))

    if response.status_code >= 400:
        logger.warning(
            "%s request returned status %s",
            operation,
            response.status_code,
        )
        return Result.failure(map_http_status(response.status_code))

    try:
        return Result.success(response.json())
    except ValueError:
        logger.warning("%s response was not valid JSON.", operation)
        return Result.failure(invalid_response_error())
