import asyncio
from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest
from bson import ObjectId
from pymongo.errors import PyMongoError

from src.business_logic.vector_business_logic import (
    VectorBusinessLogic,
    chunk_vector_id,
)
from src.constants import ErrorCode, ErrorMessage
from src.helpers.result_pattern import ErrorType, Result, ResultError
from src.llm.contracts import EmbeddingProvider
from src.llm.factories import EmbeddingProviderFactory
from src.models.project import Project
from src.repositories.data_chunk_repository import DataChunkRepository
from src.repositories.project_repository import ProjectRepository
from src.vector_db.VectorDBInterface import VectorStore
from src.vector_db.VectorDBModels import VectorSearchFilter, VectorSearchResult


COLLECTION_NAME = "test_chunks"


@pytest.fixture
def chunk_repository():
    return AsyncMock(spec=DataChunkRepository)


@pytest.fixture
def project_repository():
    return AsyncMock(spec=ProjectRepository)


@pytest.fixture
def embedding_provider():
    return AsyncMock(spec=EmbeddingProvider)


@pytest.fixture
def embedding_factory(embedding_provider):
    factory = Mock(spec=EmbeddingProviderFactory)
    factory.create.return_value = Result.success(embedding_provider)
    return factory


@pytest.fixture
def vector_store():
    return AsyncMock(spec=VectorStore)


@pytest.fixture
def logic(
    chunk_repository,
    project_repository,
    embedding_factory,
    vector_store,
):
    return VectorBusinessLogic(
        chunk_repository=chunk_repository,
        project_repository=project_repository,
        embedding_factory=embedding_factory,
        vector_store=vector_store,
        collection_name=COLLECTION_NAME,
    )


def make_error(code=ErrorCode.LLM_PROVIDER_ERROR):
    return ResultError(
        code=code,
        message=ErrorMessage.LLM_PROVIDER_ERROR,
        type=ErrorType.INTERNAL,
    )


def test_chunk_vector_id_is_deterministic_and_uuid_compatible():
    chunk_id = ObjectId()

    first = chunk_vector_id(chunk_id)
    second = chunk_vector_id(chunk_id)

    assert first == second
    assert first != chunk_vector_id(ObjectId())
    assert str(UUID(first)) == first


def test_index_project_stores_embeddings_and_metadata_without_reset(
    logic,
    chunk_repository,
    project_repository,
    embedding_provider,
    embedding_factory,
    vector_store,
    project,
    make_data_chunk,
):
    asset_id = ObjectId()
    chunks = [
        make_data_chunk(
            project.id,
            asset_id,
            text="first chunk",
            order=1,
            chunk_id=ObjectId(),
        ),
        make_data_chunk(
            project.id,
            asset_id,
            text="second chunk",
            order=2,
            chunk_id=ObjectId(),
        ),
    ]
    project_repository.get_by_project_id.return_value = project
    chunk_repository.get_all_by_project_id.return_value = chunks
    embedding_provider.embed.side_effect = [
        Result.success([1.0, 0.0, 0.0, 0.0]),
        Result.success([0.0, 1.0, 0.0, 0.0]),
    ]
    vector_store.upsert.return_value = Result.success(2)

    result = asyncio.run(logic.index_project(project.project_id))

    assert result.is_success is True
    assert result.value == 2

    project_repository.get_by_project_id.assert_awaited_once_with(
        project.project_id
    )
    chunk_repository.get_all_by_project_id.assert_awaited_once_with(
        project.id
    )
    embedding_factory.create.assert_called_once_with()
    assert embedding_provider.embed.await_count == 2
    assert [
        call.args[0] for call in embedding_provider.embed.await_args_list
    ] == ["first chunk", "second chunk"]

    vector_store.list_ids_by_project.assert_not_awaited()
    vector_store.delete_by_ids.assert_not_awaited()

    collection_name, records = vector_store.upsert.await_args.args
    assert collection_name == COLLECTION_NAME
    assert [record.vector_id for record in records] == [
        chunk_vector_id(chunk.id) for chunk in chunks
    ]
    assert [record.vector for record in records] == [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
    ]
    assert records[0].metadata == {
        "project_id": project.project_id,
        "asset_id": str(asset_id),
        "chunk_id": str(chunks[0].id),
        "chunk_index": 1,
        "text": "first chunk",
    }


def test_index_project_with_reset_deletes_only_stale_vectors(
    logic,
    chunk_repository,
    project_repository,
    embedding_provider,
    vector_store,
    project,
    make_data_chunk,
):
    chunk = make_data_chunk(
        project.id,
        ObjectId(),
        text="kept chunk",
        order=1,
        chunk_id=ObjectId(),
    )
    stale_id = chunk_vector_id(ObjectId())
    project_repository.get_by_project_id.return_value = project
    chunk_repository.get_all_by_project_id.return_value = [chunk]
    embedding_provider.embed.return_value = Result.success(
        [1.0, 0.0, 0.0, 0.0]
    )
    vector_store.list_ids_by_project.return_value = Result.success(
        [chunk_vector_id(chunk.id), stale_id]
    )
    vector_store.upsert.return_value = Result.success(1)
    vector_store.delete_by_ids.return_value = Result.success(None)

    result = asyncio.run(
        logic.index_project(project.project_id, do_reset=True)
    )

    assert result.is_success is True
    assert result.value == 1
    vector_store.list_ids_by_project.assert_awaited_once_with(
        COLLECTION_NAME,
        project.project_id,
    )
    vector_store.delete_by_ids.assert_awaited_once_with(
        COLLECTION_NAME,
        [stale_id],
    )


def test_index_project_with_reset_skips_delete_when_all_vectors_are_current(
    logic,
    chunk_repository,
    project_repository,
    embedding_provider,
    vector_store,
    project,
    make_data_chunk,
):
    chunk = make_data_chunk(
        project.id,
        ObjectId(),
        chunk_id=ObjectId(),
    )
    project_repository.get_by_project_id.return_value = project
    chunk_repository.get_all_by_project_id.return_value = [chunk]
    embedding_provider.embed.return_value = Result.success(
        [1.0, 0.0, 0.0, 0.0]
    )
    vector_store.list_ids_by_project.return_value = Result.success(
        [chunk_vector_id(chunk.id)]
    )
    vector_store.upsert.return_value = Result.success(1)

    result = asyncio.run(
        logic.index_project(project.project_id, do_reset=True)
    )

    assert result.is_success is True
    vector_store.delete_by_ids.assert_not_awaited()


def test_index_project_preserves_existing_vectors_when_embedding_fails(
    logic,
    chunk_repository,
    project_repository,
    embedding_provider,
    vector_store,
    project,
    make_data_chunk,
):
    error = make_error()
    chunks = [
        make_data_chunk(
            project.id,
            ObjectId(),
            text="good chunk",
            order=1,
            chunk_id=ObjectId(),
        ),
        make_data_chunk(
            project.id,
            ObjectId(),
            text="failing chunk",
            order=2,
            chunk_id=ObjectId(),
        ),
    ]
    project_repository.get_by_project_id.return_value = project
    chunk_repository.get_all_by_project_id.return_value = chunks
    embedding_provider.embed.side_effect = [
        Result.success([1.0, 0.0, 0.0, 0.0]),
        Result.failure(error),
    ]

    result = asyncio.run(
        logic.index_project(project.project_id, do_reset=True)
    )

    assert result.is_success is False
    assert result.error is error
    vector_store.list_ids_by_project.assert_not_awaited()
    vector_store.upsert.assert_not_awaited()
    vector_store.delete_by_ids.assert_not_awaited()


def test_index_project_preserves_existing_vectors_when_upsert_fails(
    logic,
    chunk_repository,
    project_repository,
    embedding_provider,
    vector_store,
    project,
    make_data_chunk,
):
    error = make_error(ErrorCode.VECTOR_DB_UPSERT_FAILED)
    chunk = make_data_chunk(
        project.id,
        ObjectId(),
        chunk_id=ObjectId(),
    )
    project_repository.get_by_project_id.return_value = project
    chunk_repository.get_all_by_project_id.return_value = [chunk]
    embedding_provider.embed.return_value = Result.success(
        [1.0, 0.0, 0.0, 0.0]
    )
    vector_store.list_ids_by_project.return_value = Result.success(
        [chunk_vector_id(ObjectId())]
    )
    vector_store.upsert.return_value = Result.failure(error)

    result = asyncio.run(
        logic.index_project(project.project_id, do_reset=True)
    )

    assert result.is_success is False
    assert result.error is error
    vector_store.delete_by_ids.assert_not_awaited()


def test_index_project_preserves_existing_vectors_when_lookup_fails(
    logic,
    chunk_repository,
    project_repository,
    embedding_provider,
    vector_store,
    project,
    make_data_chunk,
):
    error = make_error(ErrorCode.VECTOR_DB_PROJECT_VECTOR_LOOKUP_FAILED)
    chunk = make_data_chunk(
        project.id,
        ObjectId(),
        chunk_id=ObjectId(),
    )
    project_repository.get_by_project_id.return_value = project
    chunk_repository.get_all_by_project_id.return_value = [chunk]
    embedding_provider.embed.return_value = Result.success(
        [1.0, 0.0, 0.0, 0.0]
    )
    vector_store.list_ids_by_project.return_value = Result.failure(error)

    result = asyncio.run(
        logic.index_project(project.project_id, do_reset=True)
    )

    assert result.is_success is False
    assert result.error is error
    vector_store.upsert.assert_not_awaited()
    vector_store.delete_by_ids.assert_not_awaited()


def test_index_project_returns_delete_failure_after_storing_new_vectors(
    logic,
    chunk_repository,
    project_repository,
    embedding_provider,
    vector_store,
    project,
    make_data_chunk,
):
    error = make_error(ErrorCode.VECTOR_DB_DELETE_FAILED)
    chunk = make_data_chunk(
        project.id,
        ObjectId(),
        chunk_id=ObjectId(),
    )
    stale_id = chunk_vector_id(ObjectId())
    project_repository.get_by_project_id.return_value = project
    chunk_repository.get_all_by_project_id.return_value = [chunk]
    embedding_provider.embed.return_value = Result.success(
        [1.0, 0.0, 0.0, 0.0]
    )
    vector_store.list_ids_by_project.return_value = Result.success(
        [stale_id]
    )
    vector_store.upsert.return_value = Result.success(1)
    vector_store.delete_by_ids.return_value = Result.failure(error)

    result = asyncio.run(
        logic.index_project(project.project_id, do_reset=True)
    )

    assert result.is_success is False
    assert result.error is error
    vector_store.upsert.assert_awaited_once()


def test_index_project_rejects_missing_project(
    logic,
    chunk_repository,
    project_repository,
    embedding_factory,
    vector_store,
):
    project_repository.get_by_project_id.return_value = None

    result = asyncio.run(logic.index_project("missing-project"))

    assert result.is_success is False
    assert result.error.code == ErrorCode.PROJECT_NOT_FOUND
    assert result.error.type is ErrorType.NOT_FOUND
    chunk_repository.get_all_by_project_id.assert_not_awaited()
    embedding_factory.create.assert_not_called()
    vector_store.upsert.assert_not_awaited()


def test_index_project_rejects_project_without_object_id(
    logic,
    chunk_repository,
    project_repository,
    embedding_factory,
    vector_store,
):
    project_repository.get_by_project_id.return_value = Project(
        project_id="project-1"
    )

    result = asyncio.run(logic.index_project("project-1"))

    assert result.is_success is False
    assert result.error.code == ErrorCode.INVALID_PROJECT_ID
    assert result.error.type is ErrorType.INTERNAL
    chunk_repository.get_all_by_project_id.assert_not_awaited()
    embedding_factory.create.assert_not_called()
    vector_store.upsert.assert_not_awaited()


def test_index_project_maps_chunk_lookup_failure(
    logic,
    chunk_repository,
    project_repository,
    embedding_factory,
    vector_store,
    project,
):
    project_repository.get_by_project_id.return_value = project
    chunk_repository.get_all_by_project_id.side_effect = PyMongoError(
        "lookup failed"
    )

    result = asyncio.run(logic.index_project(project.project_id))

    assert result.is_success is False
    assert result.error.code == ErrorCode.CHUNK_LOOKUP_FAILED
    assert result.error.type is ErrorType.INTERNAL
    embedding_factory.create.assert_not_called()
    vector_store.upsert.assert_not_awaited()


def test_index_project_rejects_project_without_chunks(
    logic,
    chunk_repository,
    project_repository,
    embedding_factory,
    vector_store,
    project,
):
    project_repository.get_by_project_id.return_value = project
    chunk_repository.get_all_by_project_id.return_value = []

    result = asyncio.run(
        logic.index_project(project.project_id, do_reset=True)
    )

    assert result.is_success is False
    assert result.error.code == ErrorCode.NO_CHUNKS_TO_INDEX
    assert result.error.type is ErrorType.UNPROCESSABLE
    embedding_factory.create.assert_not_called()
    vector_store.list_ids_by_project.assert_not_awaited()
    vector_store.upsert.assert_not_awaited()
    vector_store.delete_by_ids.assert_not_awaited()


def test_index_project_propagates_embedding_factory_failure(
    logic,
    chunk_repository,
    project_repository,
    embedding_factory,
    vector_store,
    project,
    make_data_chunk,
):
    error = make_error(ErrorCode.LLM_PROVIDER_UNSUPPORTED)
    project_repository.get_by_project_id.return_value = project
    chunk_repository.get_all_by_project_id.return_value = [
        make_data_chunk(project.id, ObjectId())
    ]
    embedding_factory.create.return_value = Result.failure(error)

    result = asyncio.run(logic.index_project(project.project_id))

    assert result.is_success is False
    assert result.error is error
    vector_store.upsert.assert_not_awaited()
    vector_store.delete_by_ids.assert_not_awaited()


def test_index_project_rejects_chunk_without_id(
    logic,
    chunk_repository,
    project_repository,
    embedding_provider,
    vector_store,
    project,
    make_data_chunk,
):
    chunk = make_data_chunk(project.id, ObjectId(), chunk_id=None)
    project_repository.get_by_project_id.return_value = project
    chunk_repository.get_all_by_project_id.return_value = [chunk]

    result = asyncio.run(logic.index_project(project.project_id))

    assert result.is_success is False
    assert result.error.code == ErrorCode.INVALID_CHUNK_ID
    assert result.error.type is ErrorType.INTERNAL
    embedding_provider.embed.assert_not_awaited()
    vector_store.upsert.assert_not_awaited()
    vector_store.delete_by_ids.assert_not_awaited()


def test_search_project_embeds_trimmed_query_and_filters_by_project(
    logic,
    project_repository,
    embedding_provider,
    vector_store,
    project,
):
    matches = [
        VectorSearchResult(
            vector_id=str(ObjectId()),
            score=0.9,
            metadata={"project_id": project.project_id},
        )
    ]
    project_repository.get_by_project_id.return_value = project
    embedding_provider.embed.return_value = Result.success(
        [1.0, 0.0, 0.0, 0.0]
    )
    vector_store.search.return_value = Result.success(matches)

    result = asyncio.run(
        logic.search_project(project.project_id, "  alpha query  ", limit=3)
    )

    assert result.is_success is True
    assert result.value == matches
    project_repository.get_by_project_id.assert_awaited_once_with(
        project.project_id
    )
    embedding_provider.embed.assert_awaited_once_with("alpha query")

    collection_name, query_vector = vector_store.search.await_args.args
    assert collection_name == COLLECTION_NAME
    assert query_vector == [1.0, 0.0, 0.0, 0.0]

    kwargs = vector_store.search.await_args.kwargs
    assert kwargs["limit"] == 3
    assert kwargs["filters"] == VectorSearchFilter(
        project_id=project.project_id
    )


@pytest.mark.parametrize("query", ["", "   ", "\n\t"])
def test_search_project_rejects_empty_query(
    logic,
    project_repository,
    embedding_provider,
    vector_store,
    query,
):
    result = asyncio.run(logic.search_project("project-1", query))

    assert result.is_success is False
    assert result.error.code == ErrorCode.EMPTY_SEARCH_QUERY
    assert result.error.type is ErrorType.VALIDATION
    project_repository.get_by_project_id.assert_not_awaited()
    embedding_provider.embed.assert_not_awaited()
    vector_store.search.assert_not_awaited()


@pytest.mark.parametrize("limit", [0, -1])
def test_search_project_rejects_non_positive_limit(
    logic,
    project_repository,
    embedding_provider,
    vector_store,
    limit,
):
    result = asyncio.run(
        logic.search_project("project-1", "query", limit=limit)
    )

    assert result.is_success is False
    assert result.error.code == ErrorCode.VECTOR_DB_INVALID_SEARCH_LIMIT
    assert result.error.type is ErrorType.VALIDATION
    project_repository.get_by_project_id.assert_not_awaited()
    embedding_provider.embed.assert_not_awaited()
    vector_store.search.assert_not_awaited()


def test_search_project_rejects_missing_project(
    logic,
    project_repository,
    embedding_factory,
    vector_store,
):
    project_repository.get_by_project_id.return_value = None

    result = asyncio.run(logic.search_project("missing-project", "query"))

    assert result.is_success is False
    assert result.error.code == ErrorCode.PROJECT_NOT_FOUND
    assert result.error.type is ErrorType.NOT_FOUND
    embedding_factory.create.assert_not_called()
    vector_store.search.assert_not_awaited()


def test_search_project_rejects_project_without_object_id(
    logic,
    project_repository,
    embedding_factory,
    vector_store,
):
    project_repository.get_by_project_id.return_value = Project(
        project_id="project-1"
    )

    result = asyncio.run(logic.search_project("project-1", "query"))

    assert result.is_success is False
    assert result.error.code == ErrorCode.INVALID_PROJECT_ID
    assert result.error.type is ErrorType.INTERNAL
    embedding_factory.create.assert_not_called()
    vector_store.search.assert_not_awaited()


def test_search_project_propagates_embedding_factory_failure(
    logic,
    project_repository,
    embedding_factory,
    vector_store,
    project,
):
    error = make_error(ErrorCode.LLM_PROVIDER_UNSUPPORTED)
    project_repository.get_by_project_id.return_value = project
    embedding_factory.create.return_value = Result.failure(error)

    result = asyncio.run(logic.search_project(project.project_id, "query"))

    assert result.is_success is False
    assert result.error is error
    vector_store.search.assert_not_awaited()


def test_search_project_propagates_embedding_failure(
    logic,
    project_repository,
    embedding_provider,
    vector_store,
    project,
):
    error = make_error(ErrorCode.LLM_PROVIDER_ERROR)
    project_repository.get_by_project_id.return_value = project
    embedding_provider.embed.return_value = Result.failure(error)

    result = asyncio.run(logic.search_project(project.project_id, "query"))

    assert result.is_success is False
    assert result.error is error
    vector_store.search.assert_not_awaited()


def test_search_project_propagates_vector_store_failure(
    logic,
    project_repository,
    embedding_provider,
    vector_store,
    project,
):
    error = make_error(ErrorCode.VECTOR_DB_SEARCH_FAILED)
    project_repository.get_by_project_id.return_value = project
    embedding_provider.embed.return_value = Result.success(
        [1.0, 0.0, 0.0, 0.0]
    )
    vector_store.search.return_value = Result.failure(error)

    result = asyncio.run(logic.search_project(project.project_id, "query"))

    assert result.is_success is False
    assert result.error is error


def test_search_project_treats_missing_vector_results_as_empty(
    logic,
    project_repository,
    embedding_provider,
    vector_store,
    project,
):
    project_repository.get_by_project_id.return_value = project
    embedding_provider.embed.return_value = Result.success(
        [1.0, 0.0, 0.0, 0.0]
    )
    vector_store.search.return_value = Result.success(None)

    result = asyncio.run(logic.search_project(project.project_id, "query"))

    assert result.is_success is True
    assert result.value == []
