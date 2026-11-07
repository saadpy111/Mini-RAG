"""Registered vector database provider builders."""

from collections.abc import Sequence

from qdrant_client import AsyncQdrantClient

from src.vector_db.VectorDBInterface import VectorDBInterface
from src.vector_db.VectorDBModels import VectorCollectionConfig
from src.vector_db.providers.QdrantDBConfig import QdrantDBConfig
from src.vector_db.providers.QdrantDBProvider import QdrantDBProvider


def build_qdrant_provider(
    collections: Sequence[VectorCollectionConfig],
) -> VectorDBInterface:
    """Create the Qdrant provider using one shared async client."""

    config = QdrantDBConfig.from_environment()
    client = AsyncQdrantClient(
        url=config.url,
        api_key=config.api_key or None,
        timeout=config.timeout,
    )

    return QdrantDBProvider(
        client=client,
        collections=collections,
    )


VECTOR_DB_PROVIDER_BUILDERS = {
    "qdrant": build_qdrant_provider,
}
