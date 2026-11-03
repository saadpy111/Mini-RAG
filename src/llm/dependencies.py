"""FastAPI dependencies for the LLM provider factories."""

from fastapi import Request

from src.helpers.config import settings
from src.llm.factories import ChatProviderFactory, EmbeddingProviderFactory
from src.llm.providers.provider_registry import (
    CHAT_PROVIDER_BUILDERS,
    EMBEDDING_PROVIDER_BUILDERS,
)


def get_chat_provider_factory(request: Request) -> ChatProviderFactory:
    return ChatProviderFactory(
        builders=CHAT_PROVIDER_BUILDERS,
        http_client=request.app.state.llm_http_client,
        default_provider=settings.chat_provider,
        default_model=settings.chat_model,
    )


def get_embedding_provider_factory(
    request: Request,
) -> EmbeddingProviderFactory:
    return EmbeddingProviderFactory(
        builders=EMBEDDING_PROVIDER_BUILDERS,
        http_client=request.app.state.llm_http_client,
        default_provider=settings.embedding_provider,
        default_model=settings.embedding_model,
    )
