"""OpenRouter chat-completion provider."""

import logging
from typing import Any, Sequence

import httpx

from src.helpers.result_pattern import Result
from src.llm.contracts import ChatCompletionOutput, ChatMessage, ChatProvider
from src.llm.errors import invalid_chat_messages_error, invalid_response_error
from src.llm.providers.openrouter.config import OpenRouterProviderConfig
from src.llm.providers.openrouter.http import CHAT_COMPLETIONS_PATH, post_json

logger = logging.getLogger(__name__)


class OpenRouterChatProvider(ChatProvider):
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
    ) -> "OpenRouterChatProvider":
        """Build a provider using OpenRouter environment configuration."""
        return cls(
            client=client,
            config=OpenRouterProviderConfig.from_environment(),
            model_id=model_id,
        )

    async def complete(
        self,
        messages: Sequence[ChatMessage],
    ) -> Result[ChatCompletionOutput]:
        if not messages:
            return Result.failure(invalid_chat_messages_error())

        payload = {
            "model": self.model_id,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in messages
            ],
        }

        response_result = await post_json(
            self._client,
            base_url=self._config.base_url,
            path=CHAT_COMPLETIONS_PATH,
            payload=payload,
            api_key=self._config.api_key,
            operation="OpenRouter chat",
        )
        if not response_result.is_success:
            return Result.failure(response_result.error)

        output = self._parse_response(response_result.value)
        if output is None:
            logger.warning("OpenRouter chat response had an unexpected shape.")
            return Result.failure(invalid_response_error())

        return Result.success(output)

    def _parse_response(self, payload: Any) -> ChatCompletionOutput | None:
        if not isinstance(payload, dict):
            return None

        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            return None

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            return None

        message = first_choice.get("message")
        if not isinstance(message, dict):
            return None

        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            logger.debug(
                "OpenRouter chat returned empty content (finish_reason=%s).",
                first_choice.get("finish_reason"),
            )
            return None

        served_model = payload.get("model")
        if not isinstance(served_model, str) or not served_model:
            served_model = self.model_id

        return ChatCompletionOutput(content=content, model=served_model)
