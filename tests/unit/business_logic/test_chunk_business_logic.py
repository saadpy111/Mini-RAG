import asyncio
from unittest.mock import AsyncMock

import pytest
from bson import ObjectId
from langchain_core.documents import Document
from pymongo.errors import PyMongoError

from src.business_logic.chunk_business_logic import (
    ChunkBusinessLogic,
    build_data_chunks,
)
from src.helpers.result_pattern import ErrorType
from src.repositories.data_chunk_repository import DataChunkRepository
from src.repositories.project_repository import ProjectRepository


@pytest.fixture
def chunk_repository():
    return AsyncMock(spec=DataChunkRepository)


@pytest.fixture
def project_repository():
    return AsyncMock(spec=ProjectRepository)


@pytest.fixture
def logic(chunk_repository, project_repository):
    return ChunkBusinessLogic(
        chunk_repository=chunk_repository,
        project_repository=project_repository,
    )


def test_build_data_chunks_assigns_scope_metadata_and_order(make_data_chunk):
    project_id = ObjectId()
    asset_id = ObjectId()
    documents = [
        Document(page_content="first", metadata={"source": "a.txt"}),
        Document(page_content="second", metadata={"source": "a.txt"}),
        Document(page_content="third", metadata={"source": "a.txt"}),
    ]

    chunks = build_data_chunks(documents, project_id, asset_id)

    assert len(chunks) == 3
    assert [chunk.chunk_order for chunk in chunks] == [1, 2, 3]
    assert [chunk.chunk_text for chunk in chunks] == ["first", "second", "third"]
    assert all(chunk.chunk_project_id == project_id for chunk in chunks)
    assert all(chunk.chunk_asset_id == asset_id for chunk in chunks)
    assert all(
        chunk.chunk_metadata == {"source": "a.txt"}
        for chunk in chunks
    )


def test_build_data_chunks_returns_empty_list_for_no_documents():
    assert build_data_chunks([], ObjectId(), ObjectId()) == []


def test_create_chunk_succeeds_for_existing_project(
    logic,
    chunk_repository,
    project_repository,
    project,
    asset,
    make_data_chunk,
):
    chunk = make_data_chunk(project.id, asset.id)
    project_repository.get_by_id.return_value = project
    chunk_repository.create_chunk.return_value = chunk

    result = asyncio.run(logic.create_chunk(chunk))

    assert result.is_success is True
    assert result.value is chunk
    chunk_repository.create_chunk.assert_awaited_once_with(chunk)


def test_create_chunk_rejects_missing_project(
    logic,
    chunk_repository,
    project_repository,
    project,
    asset,
    make_data_chunk,
):
    chunk = make_data_chunk(project.id, asset.id)
    project_repository.get_by_id.return_value = None

    result = asyncio.run(logic.create_chunk(chunk))

    assert result.is_success is False
    assert result.error.code == "project_not_found"
    assert result.error.type is ErrorType.NOT_FOUND
    chunk_repository.create_chunk.assert_not_awaited()


def test_insert_many_chunks_succeeds(
    logic,
    chunk_repository,
    project_repository,
    project,
    asset,
    make_data_chunk,
):
    chunks = [
        make_data_chunk(project.id, asset.id, text="one", order=1),
        make_data_chunk(project.id, asset.id, text="two", order=2),
        make_data_chunk(project.id, asset.id, text="three", order=3),
    ]
    project_repository.get_by_id.return_value = project
    chunk_repository.insert_many_chunks.return_value = 3

    result = asyncio.run(logic.insert_many_chunks(chunks))

    assert result.is_success is True
    assert result.value == 3
    chunk_repository.insert_many_chunks.assert_awaited_once_with(
        chunks=chunks,
        batch_size=100,
    )


def test_insert_many_chunks_rejects_empty_list(
    logic,
    chunk_repository,
):
    result = asyncio.run(logic.insert_many_chunks([]))

    assert result.is_success is False
    assert result.error.code == "empty_chunks"
    assert result.error.type is ErrorType.VALIDATION
    chunk_repository.insert_many_chunks.assert_not_awaited()


@pytest.mark.parametrize("batch_size", [0, -1])
def test_insert_many_chunks_rejects_invalid_batch_size(
    logic,
    chunk_repository,
    project,
    asset,
    make_data_chunk,
    batch_size,
):
    chunks = [make_data_chunk(project.id, asset.id)]

    result = asyncio.run(
        logic.insert_many_chunks(chunks, batch_size=batch_size)
    )

    assert result.is_success is False
    assert result.error.code == "invalid_batch_size"
    assert result.error.type is ErrorType.VALIDATION
    chunk_repository.insert_many_chunks.assert_not_awaited()


def test_insert_many_chunks_rejects_project_mismatch(
    logic,
    chunk_repository,
    project_repository,
    project,
    asset,
    make_data_chunk,
):
    chunks = [
        make_data_chunk(project.id, asset.id, order=1),
        make_data_chunk(ObjectId(), asset.id, order=2),
    ]

    result = asyncio.run(logic.insert_many_chunks(chunks))

    assert result.is_success is False
    assert result.error.code == "project_id_mismatch"
    assert result.error.type is ErrorType.VALIDATION
    project_repository.get_by_id.assert_not_awaited()
    chunk_repository.insert_many_chunks.assert_not_awaited()


def test_insert_many_chunks_rejects_asset_mismatch(
    logic,
    chunk_repository,
    project_repository,
    project,
    asset,
    make_data_chunk,
):
    chunks = [
        make_data_chunk(project.id, asset.id, order=1),
        make_data_chunk(project.id, ObjectId(), order=2),
    ]

    result = asyncio.run(logic.insert_many_chunks(chunks))

    assert result.is_success is False
    assert result.error.code == "asset_id_mismatch"
    assert result.error.type is ErrorType.VALIDATION
    project_repository.get_by_id.assert_not_awaited()
    chunk_repository.insert_many_chunks.assert_not_awaited()


def test_insert_many_chunks_rejects_missing_project(
    logic,
    chunk_repository,
    project_repository,
    project,
    asset,
    make_data_chunk,
):
    chunks = [make_data_chunk(project.id, asset.id)]
    project_repository.get_by_id.return_value = None

    result = asyncio.run(logic.insert_many_chunks(chunks))

    assert result.is_success is False
    assert result.error.code == "project_not_found"
    assert result.error.type is ErrorType.NOT_FOUND
    chunk_repository.insert_many_chunks.assert_not_awaited()


def test_insert_many_chunks_maps_repository_failure(
    logic,
    chunk_repository,
    project_repository,
    project,
    asset,
    make_data_chunk,
):
    chunks = [make_data_chunk(project.id, asset.id)]
    project_repository.get_by_id.return_value = project
    chunk_repository.insert_many_chunks.side_effect = PyMongoError("write failed")

    result = asyncio.run(logic.insert_many_chunks(chunks))

    assert result.is_success is False
    assert result.error.code == "chunk_persistence_failed"
    assert result.error.type is ErrorType.INTERNAL


def test_replace_chunks_for_asset_deletes_only_captured_old_ids(
    logic,
    chunk_repository,
    project_repository,
    project,
    asset,
    make_data_chunk,
):
    old_ids = [ObjectId(), ObjectId()]
    new_chunks = [
        make_data_chunk(project.id, asset.id, text="new one", order=1),
        make_data_chunk(project.id, asset.id, text="new two", order=2),
    ]
    project_repository.get_by_id.return_value = project
    chunk_repository.get_chunk_ids_by_project_and_asset.return_value = old_ids
    chunk_repository.insert_many_chunks.return_value = len(new_chunks)
    chunk_repository.delete_by_ids.return_value = len(old_ids)

    result = asyncio.run(
        logic.replace_chunks_for_asset(
            project_id=project.id,
            asset_id=asset.id,
            chunks=new_chunks,
        )
    )

    assert result.is_success is True
    assert result.value == len(new_chunks)
    chunk_repository.get_chunk_ids_by_project_and_asset.assert_awaited_once_with(
        project_id=project.id,
        asset_id=asset.id,
    )
    chunk_repository.insert_many_chunks.assert_awaited_once_with(
        chunks=new_chunks,
        batch_size=100,
    )
    chunk_repository.delete_by_ids.assert_awaited_once_with(old_ids)


def test_replace_chunks_for_asset_preserves_old_chunks_when_insert_fails(
    logic,
    chunk_repository,
    project_repository,
    project,
    asset,
    make_data_chunk,
):
    old_ids = [ObjectId(), ObjectId()]
    new_chunks = [make_data_chunk(project.id, asset.id)]
    project_repository.get_by_id.return_value = project
    chunk_repository.get_chunk_ids_by_project_and_asset.return_value = old_ids
    chunk_repository.insert_many_chunks.side_effect = PyMongoError("write failed")

    result = asyncio.run(
        logic.replace_chunks_for_asset(
            project_id=project.id,
            asset_id=asset.id,
            chunks=new_chunks,
        )
    )

    assert result.is_success is False
    assert result.error.code == "chunk_persistence_failed"
    assert result.error.type is ErrorType.INTERNAL
    chunk_repository.delete_by_ids.assert_not_awaited()


def test_replace_chunks_for_asset_maps_lookup_failure(
    logic,
    chunk_repository,
    project_repository,
    project,
    asset,
    make_data_chunk,
):
    new_chunks = [make_data_chunk(project.id, asset.id)]
    project_repository.get_by_id.return_value = project
    chunk_repository.get_chunk_ids_by_project_and_asset.side_effect = (
        PyMongoError("lookup failed")
    )

    result = asyncio.run(
        logic.replace_chunks_for_asset(
            project_id=project.id,
            asset_id=asset.id,
            chunks=new_chunks,
        )
    )

    assert result.is_success is False
    assert result.error.code == "chunk_lookup_failed"
    assert result.error.type is ErrorType.INTERNAL
    chunk_repository.insert_many_chunks.assert_not_awaited()
    chunk_repository.delete_by_ids.assert_not_awaited()


def test_replace_chunks_for_asset_maps_cleanup_exception(
    logic,
    chunk_repository,
    project_repository,
    project,
    asset,
    make_data_chunk,
):
    old_ids = [ObjectId()]
    new_chunks = [make_data_chunk(project.id, asset.id)]
    project_repository.get_by_id.return_value = project
    chunk_repository.get_chunk_ids_by_project_and_asset.return_value = old_ids
    chunk_repository.insert_many_chunks.return_value = len(new_chunks)
    chunk_repository.delete_by_ids.side_effect = PyMongoError("delete failed")

    result = asyncio.run(
        logic.replace_chunks_for_asset(
            project_id=project.id,
            asset_id=asset.id,
            chunks=new_chunks,
        )
    )

    assert result.is_success is False
    assert result.error.code == "chunk_cleanup_failed"
    assert result.error.type is ErrorType.INTERNAL
    assert "1 replacement chunks were stored" in result.error.message


def test_replace_chunks_for_asset_reports_partial_cleanup(
    logic,
    chunk_repository,
    project_repository,
    project,
    asset,
    make_data_chunk,
):
    old_ids = [ObjectId(), ObjectId()]
    new_chunks = [make_data_chunk(project.id, asset.id)]
    project_repository.get_by_id.return_value = project
    chunk_repository.get_chunk_ids_by_project_and_asset.return_value = old_ids
    chunk_repository.insert_many_chunks.return_value = len(new_chunks)
    chunk_repository.delete_by_ids.return_value = 1

    result = asyncio.run(
        logic.replace_chunks_for_asset(
            project_id=project.id,
            asset_id=asset.id,
            chunks=new_chunks,
        )
    )

    assert result.is_success is False
    assert result.error.code == "chunk_cleanup_failed"
    assert result.error.type is ErrorType.INTERNAL
    assert "only 1 of 2 previous chunks were removed" in result.error.message


def test_replace_chunks_for_asset_skips_cleanup_without_previous_chunks(
    logic,
    chunk_repository,
    project_repository,
    project,
    asset,
    make_data_chunk,
):
    new_chunks = [make_data_chunk(project.id, asset.id)]
    project_repository.get_by_id.return_value = project
    chunk_repository.get_chunk_ids_by_project_and_asset.return_value = []
    chunk_repository.insert_many_chunks.return_value = len(new_chunks)

    result = asyncio.run(
        logic.replace_chunks_for_asset(
            project_id=project.id,
            asset_id=asset.id,
            chunks=new_chunks,
        )
    )

    assert result.is_success is True
    assert result.value == 1
    chunk_repository.delete_by_ids.assert_not_awaited()


def test_replace_chunks_for_asset_rejects_empty_chunks(
    logic,
    chunk_repository,
):
    result = asyncio.run(
        logic.replace_chunks_for_asset(
            project_id=ObjectId(),
            asset_id=ObjectId(),
            chunks=[],
        )
    )

    assert result.is_success is False
    assert result.error.code == "empty_chunks"
    assert result.error.type is ErrorType.VALIDATION
    chunk_repository.get_chunk_ids_by_project_and_asset.assert_not_awaited()


@pytest.mark.parametrize(
    "make_scope",
    [
        lambda project_id, asset_id: (ObjectId(), asset_id),
        lambda project_id, asset_id: (project_id, ObjectId()),
    ],
)
def test_replace_chunks_for_asset_rejects_scope_mismatch(
    logic,
    chunk_repository,
    project_repository,
    project,
    asset,
    make_data_chunk,
    make_scope,
):
    wrong_project_id, wrong_asset_id = make_scope(project.id, asset.id)
    chunks = [make_data_chunk(wrong_project_id, wrong_asset_id)]

    result = asyncio.run(
        logic.replace_chunks_for_asset(
            project_id=project.id,
            asset_id=asset.id,
            chunks=chunks,
        )
    )

    assert result.is_success is False
    assert result.error.code == "chunk_scope_mismatch"
    assert result.error.type is ErrorType.VALIDATION
    project_repository.get_by_id.assert_not_awaited()
    chunk_repository.get_chunk_ids_by_project_and_asset.assert_not_awaited()


def test_replace_chunks_does_not_delete_newly_inserted_ids(
    logic,
    chunk_repository,
    project_repository,
    project,
    asset,
    make_data_chunk,
):
    old_ids = [ObjectId(), ObjectId()]
    new_id = ObjectId()
    new_chunks = [
        make_data_chunk(project.id, asset.id, chunk_id=new_id),
    ]
    project_repository.get_by_id.return_value = project
    chunk_repository.get_chunk_ids_by_project_and_asset.return_value = old_ids
    chunk_repository.insert_many_chunks.return_value = 1
    chunk_repository.delete_by_ids.return_value = len(old_ids)

    result = asyncio.run(
        logic.replace_chunks_for_asset(
            project_id=project.id,
            asset_id=asset.id,
            chunks=new_chunks,
        )
    )

    assert result.is_success is True
    deleted_ids = chunk_repository.delete_by_ids.await_args.args[0]
    assert new_id not in deleted_ids
    assert set(deleted_ids) == set(old_ids)


def test_delete_by_project_id_returns_deleted_count(
    logic,
    chunk_repository,
    project_repository,
    project,
):
    project_repository.get_by_id.return_value = project
    chunk_repository.delete_by_project_id.return_value = 4

    result = asyncio.run(logic.delete_by_project_id(project.id))

    assert result.is_success is True
    assert result.value == 4


def test_delete_by_project_id_rejects_missing_project(
    logic,
    chunk_repository,
    project_repository,
    project,
):
    project_repository.get_by_id.return_value = None

    result = asyncio.run(logic.delete_by_project_id(project.id))

    assert result.is_success is False
    assert result.error.code == "project_not_found"
    chunk_repository.delete_by_project_id.assert_not_awaited()
