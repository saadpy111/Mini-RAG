"""FastAPI lifespan wiring for the shared vector database provider."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.helpers.config import settings
from src.vector_db.VectorDBProviderFactory import VectorDBProviderFactory
from src.vector_db.providers.provider_registry import (
    VECTOR_DB_PROVIDER_BUILDERS,
)


logger = logging.getLogger(__name__)


@asynccontextmanager
async def vector_db_lifespan(app: FastAPI):
    factory = VectorDBProviderFactory(
        builders=VECTOR_DB_PROVIDER_BUILDERS,
        default_provider=settings.vector_db_provider,
        collections=settings.vector_db_collections,
    )

    provider_result = factory.create()
    if not provider_result.is_success:
        logger.error(
            "Vector database provider initialization failed: %s",
            provider_result.error.message,
        )
        raise RuntimeError(provider_result.error.message)

    provider = provider_result.value

    try:
        connection_result = await provider.initialize()
        if not connection_result.is_success:
            logger.error(
                "Vector database connection failed: %s",
                connection_result.error.message,
            )
            raise RuntimeError(connection_result.error.message)

        collection_result = await provider.ensure_collections()
        if not collection_result.is_success:
            logger.error(
                "Vector database collection initialization failed: %s",
                collection_result.error.message,
            )
            raise RuntimeError(collection_result.error.message)

        app.state.vector_db_provider = provider
        yield
    finally:
        await provider.close()
