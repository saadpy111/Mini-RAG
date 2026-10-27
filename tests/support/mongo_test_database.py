"""Guarded helpers for isolated MongoDB repository tests.

The helpers in this module are the only supported way for integration-test
fixtures to perform destructive operations against a test database. Every
operation validates the selected database against the current session name and
the application's configured development database before proceeding.
"""

import asyncio
from collections.abc import Iterable
from uuid import uuid4

from pymongo.errors import PyMongoError

from src.db.indexes import create_indexes

TEST_DATABASE_PREFIX = "mini_rag_test_"
DEFAULT_TEST_COLLECTIONS = ("projects", "assets", "data_chunks")


class UnsafeTestDatabaseError(RuntimeError):
    """Raised when a destructive operation targets an unsafe database."""


class TestDatabaseUnavailableError(RuntimeError):
    """Raised when the configured MongoDB server cannot be reached."""


def new_test_database_name() -> str:
    name = f"{TEST_DATABASE_PREFIX}{uuid4().hex}"
    _require_test_name(name, "Generated test database name")
    return name


def _require_test_name(name: str, label: str) -> None:
    if not isinstance(name, str) or not name.startswith(TEST_DATABASE_PREFIX):
        raise UnsafeTestDatabaseError(
            f"{label} must start with '{TEST_DATABASE_PREFIX}'. "
            "Refusing destructive operation."
        )


def ensure_safe_test_database(
    database_name: str,
    *,
    expected_name: str,
    development_name: str,
) -> None:
    """Validate that a database is this session's isolated test database."""

    if database_name == development_name:
        raise UnsafeTestDatabaseError(
            "Refusing to perform a destructive operation on the "
            "development database."
        )

    _require_test_name(database_name, "Selected database name")
    _require_test_name(expected_name, "Expected session database name")

    if database_name != expected_name:
        raise UnsafeTestDatabaseError(
            "Selected database does not match the current test session. "
            "Refusing destructive operation."
        )


async def ensure_server_reachable(client) -> None:
    """Ping MongoDB without exposing the URI or credentials in errors."""

    try:
        await client.admin.command("ping")
    except (PyMongoError, OSError, asyncio.TimeoutError) as exc:
        raise TestDatabaseUnavailableError(
            "Configured MongoDB server is unavailable "
            f"({type(exc).__name__})."
        ) from exc


async def prepare_test_database(
    client,
    database_name: str,
    *,
    expected_name: str,
    development_name: str,
):
    """Select, validate, and initialize the isolated test database."""

    ensure_safe_test_database(
        database_name,
        expected_name=expected_name,
        development_name=development_name,
    )
    await ensure_server_reachable(client)

    database = client[database_name]
    ensure_safe_test_database(
        database.name,
        expected_name=expected_name,
        development_name=development_name,
    )
    await create_indexes(database)
    return database


async def clean_test_collections(
    database,
    *,
    expected_name: str,
    development_name: str,
    collection_names: Iterable[str] = DEFAULT_TEST_COLLECTIONS,
) -> None:
    """Delete documents only from the validated session test database."""

    ensure_safe_test_database(
        database.name,
        expected_name=expected_name,
        development_name=development_name,
    )

    for collection_name in collection_names:
        await database[collection_name].delete_many({})


async def drop_test_database(
    client,
    database_name: str,
    *,
    expected_name: str,
    development_name: str,
) -> None:
    """Drop only the exact validated database created for this session."""

    ensure_safe_test_database(
        database_name,
        expected_name=expected_name,
        development_name=development_name,
    )
    await client.drop_database(database_name)
