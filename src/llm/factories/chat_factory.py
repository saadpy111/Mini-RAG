"""Factory that creates chat providers from a registry of builders."""

from collections.abc import Callable, Mapping

import httpx

from src.helpers.result_pattern import Result
from src.llm.contracts import ChatProvider
from src.llm.errors import unsupported_provider_error


class ChatProviderFactory:
    """Select a registered builder and create a chat provider."""

    def __init__(
        self,
        *,
        builders: Mapping[
            str,
            Callable[[httpx.AsyncClient, str], ChatProvider],
        ],
        http_client: httpx.AsyncClient,
        default_provider: str,
        default_model: str,
    ) -> None:
        self._builders = builders
        self._http_client = http_client
        self._default_provider = default_provider
        self._default_model = default_model

    def create(
        self,
        provider: str | None = None,
        *,
        model: str | None = None,
    ) -> Result[ChatProvider]:
        provider_name = (
            self._default_provider if provider is None else provider
        ).strip().lower()
        builder = self._builders.get(provider_name)
        if builder is None:
            return Result.failure(unsupported_provider_error())

        model_id = self._default_model if model is None else model
        return Result.success(builder(self._http_client, model_id))
