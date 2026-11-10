"""Fixtures for vector indexing and search integration tests.

These tests use the real MongoDB test database and a real Qdrant instance.
Only the embedding provider is replaced with a deterministic test provider.
"""

import pytest
from qdrant_client import AsyncQdrantClient

from src.helpers.config import settings
from src.repositories.data_chunk_repository import DataChunkRepository
from src.repositories.project_repository import ProjectRepository
from src.vector_db.VectorDBModels import VectorCollectionConfig
from src.vector_db.providers.QdrantDBConfig import QdrantDBConfig
from src.vector_db.providers.QdrantDBProvider import QdrantDBProvider
from tests.support.mongo_test_database import clean_test_collections
from tests.support.qdrant_test_infrastructure import (
    drop_test_collection,
    new_test_collection_name,
    reset_test_collection,
)


@pytest.fixture(scope="session")
def qdrant_test_client(integration_event_loop):
    config = QdrantDBConfig.from_environment()
    client = AsyncQdrantClient(
        url=config.url,
        api_key=config.api_key or None,
        timeout=config.timeout,
    )

    try:
        integration_event_loop.run_until_complete(client.get_collections())
    except Exception as exc:
        integration_event_loop.run_until_complete(client.close())
        pytest.skip(
            "Vector integration tests skipped: Qdrant is unavailable "
            f"({type(exc).__name__})."
        )

    try:
        yield client
    finally:
        integration_event_loop.run_until_complete(client.close())


@pytest.fixture(scope="session")
def vector_collection():
    return VectorCollectionConfig(
        name=new_test_collection_name(),
        dimension=4,
    )


@pytest.fixture(scope="session")
def vector_provider(
    qdrant_test_client,
    vector_collection,
    integration_event_loop,
):
    provider = QdrantDBProvider(
        client=qdrant_test_client,
        collections=[vector_collection],
    )

    result = integration_event_loop.run_until_complete(
        provider.ensure_collections()
    )
    if not result.is_success:
        raise RuntimeError(result.error.message)

    try:
        yield provider
    finally:
        integration_event_loop.run_until_complete(
            drop_test_collection(
                qdrant_test_client,
                vector_collection.name,
            )
        )


@pytest.fixture(autouse=True)
def clean_vector_storage(
    run_async,
    mongo_test_database,
    test_database_name,
    qdrant_test_client,
    vector_provider,
    vector_collection,
):
    async def clean():
        await clean_test_collections(
            mongo_test_database,
            expected_name=test_database_name,
            development_name=settings.mongodb_database,
        )
        await reset_test_collection(
            qdrant_test_client,
            vector_provider,
            vector_collection.name,
        )

    run_async(clean())
    yield
    run_async(clean())


@pytest.fixture
def project_repository(mongo_test_database):
    return ProjectRepository(mongo_test_database)


@pytest.fixture
def chunk_repository(mongo_test_database):
    return DataChunkRepository(mongo_test_database)
