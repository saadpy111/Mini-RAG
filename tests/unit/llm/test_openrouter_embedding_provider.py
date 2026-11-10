import asyncio
import json

import httpx
import pytest

from src.constants import ErrorCode
from src.helpers.result_pattern import ErrorType
from src.llm.providers.openrouter.config import OpenRouterProviderConfig
from src.llm.providers.openrouter.embedding_provider import (
    OpenRouterEmbeddingProvider,
)

BASE_URL = "https://openrouter.ai/api/v1"
MODEL_ID = "test/embedding-model"


def make_config(api_key="test-api-key"):
    return OpenRouterProviderConfig(api_key=api_key)


async def embed_with_transport(handler, *, text="hello world", config=None):
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        provider = OpenRouterEmbeddingProvider(
            client=client,
            config=config or make_config(),
            model_id=MODEL_ID,
        )
        return await provider.embed(text)


def test_embed_sends_configured_request_and_returns_vector():
    captured = {}

    def handler(request):
        captured["url"] = str(request.url)
        captured["authorization"] = request.headers["authorization"]
        captured["content_type"] = request.headers["content-type"]
        captured["payload"] = request.read()
        return httpx.Response(
            200,
            json={"data": [{"embedding": [0.25, -0.5, 1.0]}]},
        )

    result = asyncio.run(embed_with_transport(handler))

    assert result.is_success is True
    assert result.value == [0.25, -0.5, 1.0]

    assert captured["url"] == f"{BASE_URL}/embeddings"
    assert captured["authorization"] == "Bearer test-api-key"
    assert captured["content_type"] == "application/json"
    assert json.loads(captured["payload"]) == {
        "model": MODEL_ID,
        "input": "hello world",
        "encoding_format": "float",
    }


@pytest.mark.parametrize("text", ["", "   ", "\n\t"])
def test_embed_rejects_empty_input_without_calling_provider(text):
    def handler(request):
        raise AssertionError("The provider must not be called.")

    result = asyncio.run(embed_with_transport(handler, text=text))

    assert result.is_success is False
    assert result.error.code == ErrorCode.EMPTY_EMBEDDING_INPUT
    assert result.error.type is ErrorType.VALIDATION


def test_embed_rejects_missing_api_key_without_calling_provider():
    def handler(request):
        raise AssertionError("The provider must not be called.")

    result = asyncio.run(
        embed_with_transport(handler, config=make_config(api_key=""))
    )

    assert result.is_success is False
    assert result.error.code == ErrorCode.LLM_API_KEY_MISSING


def test_embed_maps_authentication_failure():
    def handler(request):
        return httpx.Response(401, json={"error": "unauthorized"})

    result = asyncio.run(embed_with_transport(handler))

    assert result.is_success is False
    assert result.error.code == ErrorCode.LLM_AUTH_FAILED


def test_embed_maps_rate_limit_to_service_unavailable():
    def handler(request):
        return httpx.Response(429, json={"error": "rate limited"})

    result = asyncio.run(embed_with_transport(handler))

    assert result.is_success is False
    assert result.error.code == ErrorCode.LLM_RATE_LIMITED
    assert result.error.type is ErrorType.SERVICE_UNAVAILABLE


def test_embed_maps_provider_server_failure():
    def handler(request):
        return httpx.Response(500, json={"error": "server error"})

    result = asyncio.run(embed_with_transport(handler))

    assert result.is_success is False
    assert result.error.code == ErrorCode.LLM_PROVIDER_ERROR


def test_embed_maps_transport_timeout():
    def handler(request):
        raise httpx.ReadTimeout("timed out", request=request)

    result = asyncio.run(embed_with_transport(handler))

    assert result.is_success is False
    assert result.error.code == ErrorCode.LLM_TIMEOUT
    assert result.error.type is ErrorType.SERVICE_UNAVAILABLE


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"data": []},
        {"data": [{}]},
        {"data": [{"embedding": []}]},
        {"data": [{"embedding": "not-a-list"}]},
        {"data": [{"embedding": ["not-a-number"]}]},
    ],
)
def test_embed_rejects_unusable_provider_payloads(payload):
    def handler(request):
        return httpx.Response(200, json=payload)

    result = asyncio.run(embed_with_transport(handler))

    assert result.is_success is False
    assert result.error.code == ErrorCode.LLM_INVALID_RESPONSE


def test_embed_rejects_non_finite_vector_values():
    def handler(request):
        return httpx.Response(
            200,
            content=b'{"data": [{"embedding": [1.0, Infinity]}]}',
        )

    result = asyncio.run(embed_with_transport(handler))

    assert result.is_success is False
    assert result.error.code == ErrorCode.LLM_INVALID_RESPONSE


def test_embed_rejects_invalid_json_response():
    def handler(request):
        return httpx.Response(200, content=b"not-json")

    result = asyncio.run(embed_with_transport(handler))

    assert result.is_success is False
    assert result.error.code == ErrorCode.LLM_INVALID_RESPONSE
