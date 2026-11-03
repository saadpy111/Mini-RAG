"""Dictionaries of provider builder callables."""

from src.llm.providers.openrouter.chat_provider import OpenRouterChatProvider
from src.llm.providers.openrouter.embedding_provider import (
    OpenRouterEmbeddingProvider,
)

CHAT_PROVIDER_BUILDERS = {
    "openrouter": OpenRouterChatProvider.from_environment,
}

EMBEDDING_PROVIDER_BUILDERS = {
    "openrouter": OpenRouterEmbeddingProvider.from_environment,
}
