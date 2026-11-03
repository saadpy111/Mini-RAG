"""OpenRouter text-embedding provider."""

import math
from typing import Any

import httpx

from src.helpers.result_pattern import Result
from src.llm.contracts import EmbeddingProvider
from src.llm.errors import empty_embedding_input_error, invalid_response_error
from src.llm.providers.openrouter.config import OpenRouterProviderConfig
from src.llm.providers.openrouter.http import EMBEDDINGS_PATH, post_json


class OpenRouterEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        *,
        client: httpx.AsyncClient,
        config: OpenRouterProviderConfig,
        model_id: str,
    ) -> None:
        self._client = client
        self._config = config
        self.model_id = model_id

    @classmethod
    def from_environment(
        cls,
        client: httpx.AsyncClient,
        model_id: str,
    ) -> "OpenRouterEmbeddingProvider":
        """Build a provider using OpenRouter environment configuration."""
        return cls(
            client=client,
            config=OpenRouterProviderConfig.from_environment(),
            model_id=model_id,
        )

    async def embed(self, text: str) -> Result[list[float]]:
        if not isinstance(text, str) or not text.strip():
            return Result.failure(empty_embedding_input_error())

        payload = {
            "model": self.model_id,
            "input": text,
            "encoding_format": "float",
        }

        response_result = await post_json(
            self._client,
            base_url=self._config.base_url,
            path=EMBEDDINGS_PATH,
            payload=payload,
            api_key=self._config.api_key,
            operation="OpenRouter embeddings",
        )
        if not response_result.is_success:
            return Result.failure(response_result.error)

        vector = self._parse_response(response_result.value)
        if vector is None:
            return Result.failure(invalid_response_error())

        return Result.success(vector)

    def _parse_response(self, payload: Any) -> list[float] | None:
        if not isinstance(payload, dict):
            return None

        data = payload.get("data")
        if not isinstance(data, list) or not data:
            return None

        first_item = data[0]
        if not isinstance(first_item, dict):
            return None

        embedding = first_item.get("embedding")
        if not isinstance(embedding, list) or not embedding:
            return None

        try:
            vector = [float(value) for value in embedding]
        except (TypeError, ValueError):
            return None

        if not all(math.isfinite(value) for value in vector):
            return None

        return vector
