from uuid import uuid4

import pytest
from bson import ObjectId

from src.helpers.config import settings
from tests.support.mongo_test_database import (
    TEST_DATABASE_PREFIX,
    drop_test_database,
    new_test_database_name,
)

pytestmark = pytest.mark.integration


def test_session_database_is_isolated(
    mongo_test_database,
    test_database_name,
):
    assert test_database_name.startswith(TEST_DATABASE_PREFIX)
    assert mongo_test_database.name == test_database_name
    assert mongo_test_database.name != settings.mongodb_database


def test_repositories_use_the_injected_test_database(
    asset_repository,
    chunk_repository,
    mongo_test_database,
    mongo_test_client,
    test_database_name,
):
    asset_collection = asset_repository._collection
    chunk_collection = chunk_repository.collection

    assert asset_collection.database is mongo_test_database
    assert chunk_collection.database is mongo_test_database
    assert asset_collection.database.client is mongo_test_client
    assert chunk_collection.database.client is mongo_test_client
    assert asset_collection.database.name == test_database_name
    assert chunk_collection.database.name == test_database_name
    assert asset_collection.database.name != settings.mongodb_database
    assert chunk_collection.database.name != settings.mongodb_database


def test_repository_writes_stay_in_the_test_database(
    run_async,
    asset_repository,
    chunk_repository,
    make_asset,
    make_data_chunk,
    mongo_test_database,
    mongo_test_client,
):
    marker = uuid4().hex
    project_id = ObjectId()
    asset = make_asset(
        project_id,
        file_id=f"isolation-{marker}",
        asset_name=f"isolation-{marker}.txt",
    )
    chunk = make_data_chunk(
        project_id,
        asset.id,
        text=f"isolation-chunk-{marker}",
    )

    async def scenario():
        await asset_repository.create(asset)
        await chunk_repository.insert_many_chunks([chunk])

        assert (
            await mongo_test_database["assets"].count_documents(
                {"_id": asset.id}
            )
            == 1
        )
        assert (
            await mongo_test_database["data_chunks"].count_documents(
                {"chunk_text": chunk.chunk_text}
            )
            == 1
        )

        development_database = mongo_test_client[
            settings.mongodb_database
        ]
        assert development_database.name != mongo_test_database.name
        assert (
            await development_database["assets"].count_documents(
                {"_id": asset.id}
            )
            == 0
        )
        assert (
            await development_database["data_chunks"].count_documents(
                {"chunk_text": chunk.chunk_text}
            )
            == 0
        )

    run_async(scenario())


def test_temporary_test_database_cleanup_remains_scoped(
    run_async,
    mongo_test_database,
    mongo_test_client,
    test_database_name,
):
    temporary_database_name = new_test_database_name()
    session_marker = uuid4().hex

    async def scenario():
        temporary_database = mongo_test_client[temporary_database_name]

        try:
            await temporary_database["assets"].insert_one(
                {"_id": ObjectId(), "marker": "temporary"}
            )
            await mongo_test_database["assets"].insert_one(
                {"_id": ObjectId(), "marker": session_marker}
            )

            await drop_test_database(
                mongo_test_client,
                temporary_database_name,
                expected_name=temporary_database_name,
                development_name=settings.mongodb_database,
            )

            database_names = await mongo_test_client.list_database_names()
            assert temporary_database_name not in database_names
            assert test_database_name in database_names
            assert (
                await mongo_test_database["assets"].count_documents(
                    {"marker": session_marker}
                )
                == 1
            )
        finally:
            database_names = await mongo_test_client.list_database_names()
            if temporary_database_name in database_names:
                await drop_test_database(
                    mongo_test_client,
                    temporary_database_name,
                    expected_name=temporary_database_name,
                    development_name=settings.mongodb_database,
                )

    run_async(scenario())
