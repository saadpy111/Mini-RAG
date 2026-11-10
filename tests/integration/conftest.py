"""Shared fixtures for integration tests that use real infrastructure."""

import asyncio

import pytest
from pymongo import AsyncMongoClient

from src.helpers.config import settings
from tests.support.mongo_test_database import (
    TestDatabaseUnavailableError,
    drop_test_database,
    ensure_server_reachable,
    new_test_database_name,
    prepare_test_database,
)


@pytest.fixture(scope="session")
def test_database_name():
    return new_test_database_name()


@pytest.fixture(scope="session")
def integration_event_loop():
    loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        loop.close()


@pytest.fixture(scope="session")
def mongo_event_loop(integration_event_loop):
    # Backwards-compatible alias for the existing repository tests.
    return integration_event_loop


@pytest.fixture(scope="session")
def mongo_test_client(mongo_event_loop):
    client = AsyncMongoClient(
        settings.mongodb_uri,
        serverSelectionTimeoutMS=2000,
    )

    try:
        mongo_event_loop.run_until_complete(ensure_server_reachable(client))
    except TestDatabaseUnavailableError as exc:
        mongo_event_loop.run_until_complete(client.close())
        pytest.skip(f"Repository integration tests skipped: {exc}")

    try:
        yield client
    finally:
        mongo_event_loop.run_until_complete(client.close())


@pytest.fixture(scope="session")
def mongo_test_database(
    mongo_event_loop,
    mongo_test_client,
    test_database_name,
):
    try:
        database = mongo_event_loop.run_until_complete(
            prepare_test_database(
                mongo_test_client,
                test_database_name,
                expected_name=test_database_name,
                development_name=settings.mongodb_database,
            )
        )
    except BaseException as setup_error:
        try:
            mongo_event_loop.run_until_complete(
                drop_test_database(
                    mongo_test_client,
                    test_database_name,
                    expected_name=test_database_name,
                    development_name=settings.mongodb_database,
                )
            )
        except BaseException as cleanup_error:
            setup_error.add_note(
                "Test database cleanup failed after setup error: "
                f"{type(cleanup_error).__name__}."
            )
        raise

    yield database

    mongo_event_loop.run_until_complete(
        drop_test_database(
            mongo_test_client,
            test_database_name,
            expected_name=test_database_name,
            development_name=settings.mongodb_database,
        )
    )


@pytest.fixture
def run_async(mongo_event_loop):
    return mongo_event_loop.run_until_complete
