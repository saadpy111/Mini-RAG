import pytest

from src.helpers.config import settings
from src.repositories.asset_repository import AssetRepository
from src.repositories.data_chunk_repository import DataChunkRepository
from src.repositories.project_repository import ProjectRepository
from tests.support.mongo_test_database import clean_test_collections


@pytest.fixture(autouse=True)
def clean_repository_collections(
    run_async,
    mongo_test_database,
    test_database_name,
):
    async def clean():
        await clean_test_collections(
            mongo_test_database,
            expected_name=test_database_name,
            development_name=settings.mongodb_database,
        )

    run_async(clean())
    yield
    run_async(clean())


def _assert_repository_uses_test_database(
    repository,
    collection_attribute,
    database,
):
    collection = getattr(repository, collection_attribute)
    assert collection.database is database


@pytest.fixture
def asset_repository(mongo_test_database):
    repository = AssetRepository(mongo_test_database)
    _assert_repository_uses_test_database(
        repository,
        "_collection",
        mongo_test_database,
    )
    return repository


@pytest.fixture
def chunk_repository(mongo_test_database):
    repository = DataChunkRepository(mongo_test_database)
    _assert_repository_uses_test_database(
        repository,
        "collection",
        mongo_test_database,
    )
    return repository


@pytest.fixture
def project_repository(mongo_test_database):
    repository = ProjectRepository(mongo_test_database)
    _assert_repository_uses_test_database(
        repository,
        "collection",
        mongo_test_database,
    )
    return repository
