from typing import Sequence

from src.constants import ErrorCode
from src.helpers.result_pattern import Result
from src.llm.contracts import (
    ChatCompletionOutput,
    ChatMessage,
    ChatProvider,
    EmbeddingProvider,
)
from src.llm.factories import ChatProviderFactory, EmbeddingProviderFactory


class FakeChatProvider(ChatProvider):
    def __init__(self, model_id: str) -> None:
        self.model_id = model_id

    async def complete(
        self,
        messages: Sequence[ChatMessage],
    ) -> Result[ChatCompletionOutput]:
        return Result.success(
            ChatCompletionOutput(content="ok", model=self.model_id)
        )


class FakeEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model_id: str) -> None:
        self.model_id = model_id

    async def embed(self, text: str) -> Result[list[float]]:
        return Result.success([0.1, 0.2])


def test_chat_factory_resolves_registered_builder():
    http_client = object()

    def build_fake_chat_provider(client, model):
        assert client is http_client
        return FakeChatProvider(model)

    factory = ChatProviderFactory(
        builders={"fake": build_fake_chat_provider},
        http_client=http_client,
        default_provider="fake",
        default_model="default-model",
    )

    result = factory.create(provider="fake", model="test-model")

    assert result.is_success is True
    assert isinstance(result.value, FakeChatProvider)
    assert result.value.model_id == "test-model"


def test_embedding_factory_resolves_registered_builder():
    http_client = object()

    def build_fake_embedding_provider(client, model):
        assert client is http_client
        return FakeEmbeddingProvider(model)

    factory = EmbeddingProviderFactory(
        builders={"fake": build_fake_embedding_provider},
        http_client=http_client,
        default_provider="fake",
        default_model="default-model",
    )

    result = factory.create(provider="fake", model="test-model")

    assert result.is_success is True
    assert isinstance(result.value, FakeEmbeddingProvider)
    assert result.value.model_id == "test-model"


def test_factories_reject_unregistered_provider():
    chat_factory = ChatProviderFactory(
        builders={},
        http_client=object(),
        default_provider="fake",
        default_model="default-model",
    )
    embedding_factory = EmbeddingProviderFactory(
        builders={},
        http_client=object(),
        default_provider="fake",
        default_model="default-model",
    )

    chat_result = chat_factory.create(provider="missing", model="test-model")
    embedding_result = embedding_factory.create(
        provider="missing",
        model="test-model",
    )

    assert chat_result.is_success is False
    assert chat_result.error.code == ErrorCode.LLM_PROVIDER_UNSUPPORTED
    assert embedding_result.is_success is False
    assert embedding_result.error.code == ErrorCode.LLM_PROVIDER_UNSUPPORTED
