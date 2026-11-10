"""Guarded helpers for isolated Qdrant integration tests."""

import logging
from uuid import uuid4

from qdrant_client import models as qdrant_models

from src.vector_db.VectorDBInterface import VectorDBInterface

TEST_COLLECTION_PREFIX = "mini_rag_test_"
CLEAR_BATCH_SIZE = 256

logger = logging.getLogger(__name__)


def new_test_collection_name() -> str:
    return f"{TEST_COLLECTION_PREFIX}{uuid4().hex}"


def _require_test_collection_name(collection_name: str) -> None:
    if not collection_name.startswith(TEST_COLLECTION_PREFIX):
        raise RuntimeError(
            "Refusing to modify a Qdrant collection that is not an "
            "isolated test collection."
        )


async def _clear_test_collection(client, collection_name: str) -> None:
    offset = None

    while True:
        points, offset = await client.scroll(
            collection_name=collection_name,
            limit=CLEAR_BATCH_SIZE,
            offset=offset,
            with_payload=False,
            with_vectors=False,
        )

        if points:
            await client.delete(
                collection_name=collection_name,
                points_selector=qdrant_models.PointIdsList(
                    points=[str(point.id) for point in points],
                ),
                wait=True,
            )

        if offset is None:
            break


async def reset_test_collection(
    client,
    provider: VectorDBInterface,
    collection_name: str,
) -> None:
    """Clear only the isolated collection used by a test, creating it once."""

    _require_test_collection_name(collection_name)

    if await client.collection_exists(collection_name):
        await _clear_test_collection(client, collection_name)
        return

    result = await provider.ensure_collections()
    if not result.is_success:
        raise RuntimeError(result.error.message)


async def drop_test_collection(client, collection_name: str) -> None:
    """Best-effort removal of an isolated test collection.

    Qdrant running in a container on Windows-mounted volumes may be unable to
    rename collection files during deletion. Test data has already been
    cleared at that point, so cleanup failures must not fail the test run.
    """

    _require_test_collection_name(collection_name)

    try:
        if await client.collection_exists(collection_name):
            await client.delete_collection(collection_name)
    except Exception:
        logger.warning(
            "Could not drop the isolated Qdrant test collection '%s'.",
            collection_name,
            exc_info=True,
        )
