"""Factory for selecting and constructing the configured vector provider."""

import logging
from collections.abc import Callable, Mapping, Sequence

from src.helpers.result_pattern import Result
from src.vector_db.VectorDBErrors import (
    duplicate_collection_error,
    invalid_configuration_error,
    unsupported_provider_error,
)
from src.vector_db.VectorDBInterface import VectorDBInterface
from src.vector_db.VectorDBModels import VectorCollectionConfig


logger = logging.getLogger(__name__)

VectorProviderBuilder = Callable[
    [Sequence[VectorCollectionConfig]],
    VectorDBInterface,
]


class VectorDBProviderFactory:
    """Select a registered builder and construct its provider."""

    def __init__(
        self,
        *,
        builders: Mapping[str, VectorProviderBuilder],
        default_provider: str,
        collections: Sequence[VectorCollectionConfig],
    ) -> None:
        self._builders = builders
        self._default_provider = default_provider
        self._collections = tuple(collections)

    def create(
        self,
        provider: str | None = None,
    ) -> Result[VectorDBInterface]:
        if not self._collections:
            return Result.failure(invalid_configuration_error())

        configured_names: set[str] = set()

        for collection in self._collections:
            if collection.name in configured_names:
                return Result.failure(
                    duplicate_collection_error(collection.name)
                )

            configured_names.add(collection.name)

        provider_name = (
            self._default_provider if provider is None else provider
        ).strip().lower()

        builder = self._builders.get(provider_name)
        if builder is None:
            return Result.failure(unsupported_provider_error())

        try:
            return Result.success(builder(self._collections))
        except Exception:
            logger.exception(
                "Failed to construct vector database provider '%s'.",
                provider_name,
            )
            return Result.failure(invalid_configuration_error())
