"""Manual diagnostic endpoints for the configured LLM provider.

These endpoints make real provider calls and are disabled by default. They are
intended for verifying credentials and model behaviour from Swagger; no
application flow depends on them.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from src.api import to_http_response
from src.constants import ErrorMessage, SuccessMessage
from src.dtos import (
    ApiResponse,
    ChatTestRequest,
    ChatTestResultDTO,
    EmbeddingTestRequest,
    EmbeddingTestResultDTO,
)
from src.helpers import config
from src.helpers.result_pattern import Result
from src.llm.model_catalog import (
    APPROVED_CHAT_MODELS,
    APPROVED_EMBEDDING_MODELS,
)
from src.llm.contracts import ChatMessage
from src.llm.dependencies import (
    get_chat_provider_factory,
    get_embedding_provider_factory,
)
from src.llm.errors import unapproved_model_error
from src.llm.factories import ChatProviderFactory, EmbeddingProviderFactory


llm_router = APIRouter(
    prefix="/api/v1/llm",
    tags=["LLM"],
)


ChatFactory = Annotated[
    ChatProviderFactory,
    Depends(get_chat_provider_factory),
]

EmbeddingFactory = Annotated[
    EmbeddingProviderFactory,
    Depends(get_embedding_provider_factory),
]


def require_llm_test_endpoints_enabled() -> None:
    if not config.settings.llm_test_endpoints_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorMessage.LLM_TEST_ENDPOINTS_DISABLED,
        )


@llm_router.post(
    "/test/chat",
    response_model=ApiResponse[ChatTestResultDTO],
    dependencies=[Depends(require_llm_test_endpoints_enabled)],
)
async def test_chat_completion(
    chat_request: ChatTestRequest,
    chat_factory: ChatFactory,
) -> JSONResponse:
    if chat_request.model not in APPROVED_CHAT_MODELS:
        return to_http_response(Result.failure(unapproved_model_error()))

    provider_result = chat_factory.create(
        provider=config.settings.chat_provider,
        model=chat_request.model,
    )

    if not provider_result.is_success:
        return to_http_response(provider_result)

    provider = provider_result.value

    completion_result = await provider.complete(
        [ChatMessage(role="user", content=chat_request.message)]
    )

    if not completion_result.is_success:
        return to_http_response(completion_result)

    result = ChatTestResultDTO(
        model=provider.model_id,
        content=completion_result.value.content,
    )

    return to_http_response(
        Result.success(result),
        success_message=SuccessMessage.LLM_CHAT_TEST_COMPLETED,
    )


@llm_router.post(
    "/test/embeddings",
    response_model=ApiResponse[EmbeddingTestResultDTO],
    dependencies=[Depends(require_llm_test_endpoints_enabled)],
)
async def test_embeddings(
    embedding_request: EmbeddingTestRequest,
    embedding_factory: EmbeddingFactory,
) -> JSONResponse:
    if embedding_request.model not in APPROVED_EMBEDDING_MODELS:
        return to_http_response(Result.failure(unapproved_model_error()))

    provider_result = embedding_factory.create(
        provider=config.settings.embedding_provider,
        model=embedding_request.model,
    )

    if not provider_result.is_success:
        return to_http_response(provider_result)

    provider = provider_result.value

    embedding_result = await provider.embed(embedding_request.text)

    if not embedding_result.is_success:
        return to_http_response(embedding_result)

    vector = embedding_result.value

    result = EmbeddingTestResultDTO(
        model=provider.model_id,
        dimensions=len(vector),
        embedding=vector,
    )

    return to_http_response(
        Result.success(result),
        success_message=SuccessMessage.LLM_EMBEDDING_TEST_COMPLETED,
    )
