import asyncio
from unittest.mock import AsyncMock

import pytest
from pymongo.errors import ServerSelectionTimeoutError

from src.helpers.config import settings
from tests.support.mongo_test_database import (
    TEST_DATABASE_PREFIX,
    TestDatabaseUnavailableError as DatabaseUnavailableError,
    UnsafeTestDatabaseError,
    clean_test_collections,
    drop_test_database,
    ensure_safe_test_database,
    ensure_server_reachable,
    new_test_database_name,
)


class FakeAdmin:
    async def command(self, *args, **kwargs):
        raise ServerSelectionTimeoutError(
            "mongodb://user:secret@example.invalid"
        )


class FakeClient:
    def __init__(self):
        self.admin = FakeAdmin()
        self.dropped_databases = []

    async def drop_database(self, database_name):
        self.dropped_databases.append(database_name)


class FakeCollection:
    def __init__(self):
        self.delete_many = AsyncMock(return_value=0)


class FakeDatabase:
    def __init__(self, database_name):
        self.name = database_name
        self.collections = {
            "projects": FakeCollection(),
            "assets": FakeCollection(),
            "data_chunks": FakeCollection(),
        }

    def __getitem__(self, collection_name):
        return self.collections[collection_name]


def test_generated_test_database_names_are_unique_and_prefixed():
    first = new_test_database_name()
    second = new_test_database_name()

    assert first.startswith(TEST_DATABASE_PREFIX)
    assert second.startswith(TEST_DATABASE_PREFIX)
    assert first != second
    assert first != settings.mongodb_database
    assert second != settings.mongodb_database


def test_safe_test_database_name_is_accepted():
    database_name = new_test_database_name()

    ensure_safe_test_database(
        database_name,
        expected_name=database_name,
        development_name=settings.mongodb_database,
    )


@pytest.mark.parametrize(
    ("database_name", "expected_name"),
    [
        (settings.mongodb_database, settings.mongodb_database),
        ("mini_rag_other", "mini_rag_other"),
        (new_test_database_name(), new_test_database_name()),
        (new_test_database_name(), settings.mongodb_database),
    ],
)
def test_unsafe_database_names_are_rejected(
    database_name,
    expected_name,
):
    with pytest.raises(UnsafeTestDatabaseError):
        ensure_safe_test_database(
            database_name,
            expected_name=expected_name,
            development_name=settings.mongodb_database,
        )


def test_cleanup_guard_blocks_development_database_before_deletion():
    database = FakeDatabase(settings.mongodb_database)

    with pytest.raises(UnsafeTestDatabaseError):
        asyncio.run(
            clean_test_collections(
                database,
                expected_name=new_test_database_name(),
                development_name=settings.mongodb_database,
            )
        )

    for collection in database.collections.values():
        collection.delete_many.assert_not_awaited()


def test_cleanup_guard_blocks_a_different_test_database():
    database = FakeDatabase(new_test_database_name())

    with pytest.raises(UnsafeTestDatabaseError):
        asyncio.run(
            clean_test_collections(
                database,
                expected_name=new_test_database_name(),
                development_name=settings.mongodb_database,
            )
        )

    for collection in database.collections.values():
        collection.delete_many.assert_not_awaited()


def test_cleanup_deletes_only_known_collections_in_test_database():
    database_name = new_test_database_name()
    database = FakeDatabase(database_name)

    asyncio.run(
        clean_test_collections(
            database,
            expected_name=database_name,
            development_name=settings.mongodb_database,
        )
    )

    for collection in database.collections.values():
        collection.delete_many.assert_awaited_once_with({})


def test_drop_guard_blocks_development_database_before_drop():
    client = FakeClient()

    with pytest.raises(UnsafeTestDatabaseError):
        asyncio.run(
            drop_test_database(
                client,
                settings.mongodb_database,
                expected_name=settings.mongodb_database,
                development_name=settings.mongodb_database,
            )
        )

    assert client.dropped_databases == []


def test_drop_guard_blocks_a_different_test_database_before_drop():
    client = FakeClient()

    with pytest.raises(UnsafeTestDatabaseError):
        asyncio.run(
            drop_test_database(
                client,
                new_test_database_name(),
                expected_name=new_test_database_name(),
                development_name=settings.mongodb_database,
            )
        )

    assert client.dropped_databases == []


def test_drop_test_database_drops_only_expected_database():
    client = FakeClient()
    database_name = new_test_database_name()

    asyncio.run(
        drop_test_database(
            client,
            database_name,
            expected_name=database_name,
            development_name=settings.mongodb_database,
        )
    )

    assert client.dropped_databases == [database_name]


def test_unavailable_server_raises_sanitized_error():
    with pytest.raises(DatabaseUnavailableError) as exc_info:
        asyncio.run(ensure_server_reachable(FakeClient()))

    message = str(exc_info.value)
    assert "ServerSelectionTimeoutError" in message
    assert "mongodb://" not in message
    assert "secret" not in message
    assert "user" not in message
