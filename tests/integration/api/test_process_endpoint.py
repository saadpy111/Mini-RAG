from importlib import import_module

import pytest
from langchain_core.documents import Document

from src.constants import (
    ErrorCode,
    ErrorMessage,
    MessageTemplate,
    SuccessMessage,
)
from src.dependencies.dependency_injection import (
    get_asset_business_logic,
    get_chunk_business_logic,
    get_project_business_logic,
)
from src.helpers.result_pattern import ErrorType, Result, ResultError

data_router_module = import_module("src.routes.data_router")


def process_url(project_id):
    return f"/api/v1/data/process/{project_id}"


def write_asset_file(temp_files_dir, project, asset, content):
    project_dir = temp_files_dir / project.project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    file_id = asset.asset_config["file_id"]
    path = project_dir / f"{file_id}.txt"
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def process_context(
    override_business_logic,
    project_bl,
    asset_bl,
    chunk_bl,
    project,
    asset,
    temp_files_dir,
):
    override_business_logic(get_project_business_logic, project_bl)
    override_business_logic(get_asset_business_logic, asset_bl)
    override_business_logic(get_chunk_business_logic, chunk_bl)

    project_bl.get_project.return_value = Result.success(project)
    asset_bl.get_asset_by_file_id.return_value = Result.success(asset)
    write_asset_file(
        temp_files_dir,
        project,
        asset,
        "alpha bravo charlie delta echo foxtrot golf hotel",
    )

    return project_bl, asset_bl, chunk_bl


async def insert_all_chunks(chunks, batch_size=100):
    return Result.success(len(chunks))


def test_process_success_returns_lightweight_summary(
    client,
    process_context,
    project,
    asset,
    assert_api_envelope,
):
    _, asset_bl, chunk_bl = process_context
    chunk_bl.insert_many_chunks.side_effect = insert_all_chunks

    response = client.post(
        process_url(project.project_id),
        json={
            "file_id": "file-1",
            "chunk_size": 10,
            "overlap_size": 2,
        },
    )

    body = assert_api_envelope(
        response,
        is_success=True,
        status_code=200,
        message=SuccessMessage.FILE_PROCESSED,
    )

    data = body["data"]
    assert set(data) == {
        "project_id",
        "asset_id",
        "file_id",
        "is_success",
        "total_chunks",
    }
    assert data["project_id"] == project.project_id
    assert data["asset_id"] == str(asset.id)
    assert data["file_id"] == "file-1"
    assert data["is_success"] is True
    assert data["total_chunks"] > 0

    asset_bl.get_asset_by_file_id.assert_awaited_once_with(
        project_id=project.id,
        file_id="file-1",
    )
    chunk_bl.delete_by_project_id.assert_not_awaited()

    chunks = chunk_bl.insert_many_chunks.await_args.args[0]
    assert len(chunks) == data["total_chunks"]
    assert [chunk.chunk_order for chunk in chunks] == list(
        range(1, len(chunks) + 1)
    )
    assert all(chunk.chunk_project_id == project.id for chunk in chunks)
    assert all(chunk.chunk_asset_id == asset.id for chunk in chunks)


def test_process_response_does_not_include_chunk_text_or_metadata(
    client,
    process_context,
    project,
    assert_api_envelope,
):
    _, _, chunk_bl = process_context
    chunk_bl.insert_many_chunks.side_effect = insert_all_chunks

    response = client.post(
        process_url(project.project_id),
        json={"file_id": "file-1"},
    )

    assert_api_envelope(response, is_success=True, status_code=200)
    assert "alpha bravo charlie" not in response.text
    assert "chunk_text" not in response.text
    assert "chunk_metadata" not in response.text


def test_process_returns_project_not_found(
    client,
    process_context,
    project,
    assert_api_envelope,
):
    project_bl, asset_bl, chunk_bl = process_context
    project_bl.get_project.return_value = Result.failure(
        ResultError(
            code=ErrorCode.PROJECT_NOT_FOUND,
            message=ErrorMessage.PROJECT_WAS_NOT_FOUND,
            type=ErrorType.NOT_FOUND,
        )
    )

    response = client.post(
        process_url(project.project_id),
        json={"file_id": "file-1"},
    )

    body = assert_api_envelope(response, is_success=False, status_code=404)

    assert body["message"] == ErrorMessage.PROJECT_WAS_NOT_FOUND
    assert "project_not_found" not in response.text
    asset_bl.get_asset_by_file_id.assert_not_awaited()
    chunk_bl.insert_many_chunks.assert_not_awaited()


def test_process_returns_asset_not_found_for_file(
    client,
    process_context,
    project,
    assert_api_envelope,
):
    _, asset_bl, chunk_bl = process_context
    asset_bl.get_asset_by_file_id.return_value = Result.failure(
        ResultError(
            code=ErrorCode.ASSET_NOT_FOUND,
            message=ErrorMessage.ASSET_NOT_FOUND_FOR_FILE,
            type=ErrorType.NOT_FOUND,
        )
    )

    response = client.post(
        process_url(project.project_id),
        json={"file_id": "file-1"},
    )

    body = assert_api_envelope(response, is_success=False, status_code=404)

    assert body["message"] == ErrorMessage.ASSET_NOT_FOUND_FOR_FILE
    chunk_bl.insert_many_chunks.assert_not_awaited()


def test_process_rejects_asset_without_id(
    client,
    process_context,
    project,
    asset,
    assert_api_envelope,
):
    _, asset_bl, chunk_bl = process_context
    asset_bl.get_asset_by_file_id.return_value = Result.success(
        asset.model_copy(update={"id": None})
    )

    response = client.post(
        process_url(project.project_id),
        json={"file_id": "file-1"},
    )

    body = assert_api_envelope(response, is_success=False, status_code=500)

    assert body["message"] == ErrorMessage.INVALID_ASSET_ID
    chunk_bl.insert_many_chunks.assert_not_awaited()


def test_process_returns_file_not_found(
    client,
    process_context,
    project,
    temp_files_dir,
    assert_api_envelope,
):
    _, _, chunk_bl = process_context
    (temp_files_dir / project.project_id / "file-1.txt").unlink()

    response = client.post(
        process_url(project.project_id),
        json={"file_id": "file-1"},
    )

    body = assert_api_envelope(response, is_success=False, status_code=404)

    assert body["message"] == MessageTemplate.FILE_NOT_FOUND.format(
        file_id="file-1",
        project_id=project.project_id,
    )
    chunk_bl.insert_many_chunks.assert_not_awaited()


def test_process_rejects_unprocessable_empty_file(
    client,
    process_context,
    project,
    temp_files_dir,
    assert_api_envelope,
):
    _, _, chunk_bl = process_context
    (temp_files_dir / project.project_id / "file-1.txt").write_text("")

    response = client.post(
        process_url(project.project_id),
        json={"file_id": "file-1"},
    )

    body = assert_api_envelope(response, is_success=False, status_code=422)

    assert body["message"] == ErrorMessage.EMPTY_DOCUMENT_CONTENT
    chunk_bl.insert_many_chunks.assert_not_awaited()


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"file_id": ""},
        {"file_id": "file-1", "chunk_size": 0},
        {"file_id": "file-1", "overlap_size": -1},
        {"file_id": "file-1", "chunk_size": 10, "overlap_size": 10},
        {"file_id": "file-1", "chunk_size": 10, "overlap_size": 11},
    ],
)
def test_process_rejects_invalid_parameters_before_business_logic(
    client,
    process_context,
    project,
    payload,
    assert_api_envelope,
):
    project_bl, asset_bl, chunk_bl = process_context

    response = client.post(process_url(project.project_id), json=payload)

    body = assert_api_envelope(response, is_success=False, status_code=422)

    assert body["message"] == ErrorMessage.REQUEST_VALIDATION_FAILED
    project_bl.get_project.assert_not_awaited()
    asset_bl.get_asset_by_file_id.assert_not_awaited()
    chunk_bl.insert_many_chunks.assert_not_awaited()


def test_process_maps_file_content_service_failure(
    client,
    monkeypatch,
    process_context,
    project,
    assert_api_envelope,
):
    _, _, chunk_bl = process_context
    monkeypatch.setattr(
        data_router_module,
        "get_file_content",
        lambda project_id, file_id: Result.failure(
            ResultError(
                code=ErrorCode.FILE_READ_ERROR,
                message=ErrorMessage.FILE_READ_ERROR,
                type=ErrorType.INTERNAL,
            )
        ),
    )

    response = client.post(
        process_url(project.project_id),
        json={"file_id": "file-1"},
    )

    body = assert_api_envelope(response, is_success=False, status_code=500)

    assert body["message"] == ErrorMessage.FILE_READ_ERROR
    chunk_bl.insert_many_chunks.assert_not_awaited()


def test_process_maps_chunk_splitting_failure(
    client,
    monkeypatch,
    process_context,
    project,
    assert_api_envelope,
):
    _, _, chunk_bl = process_context
    monkeypatch.setattr(
        data_router_module,
        "process_file_content",
        lambda **kwargs: Result.failure(
            ResultError(
                code=ErrorCode.INVALID_CHUNK_CONFIGURATION,
                message=ErrorMessage.INVALID_CHUNK_CONFIGURATION,
                type=ErrorType.VALIDATION,
            )
        ),
    )

    response = client.post(
        process_url(project.project_id),
        json={"file_id": "file-1"},
    )

    body = assert_api_envelope(response, is_success=False, status_code=400)

    assert body["message"] == ErrorMessage.INVALID_CHUNK_CONFIGURATION
    chunk_bl.insert_many_chunks.assert_not_awaited()


def test_process_forwards_requested_chunk_configuration(
    client,
    monkeypatch,
    process_context,
    project,
    assert_api_envelope,
):
    _, _, chunk_bl = process_context
    captured = {}

    def fake_process(file_content, chunk_size, overlap_size):
        captured["chunk_size"] = chunk_size
        captured["overlap_size"] = overlap_size
        return Result.success(
            [Document(page_content="configured", metadata={"source": "x"})]
        )

    monkeypatch.setattr(
        data_router_module,
        "process_file_content",
        fake_process,
    )
    chunk_bl.insert_many_chunks.side_effect = insert_all_chunks

    response = client.post(
        process_url(project.project_id),
        json={
            "file_id": "file-1",
            "chunk_size": 42,
            "overlap_size": 7,
        },
    )

    assert_api_envelope(response, is_success=True, status_code=200)
    assert captured == {"chunk_size": 42, "overlap_size": 7}


def test_process_rejects_no_generated_chunks(
    client,
    monkeypatch,
    process_context,
    project,
    assert_api_envelope,
):
    _, _, chunk_bl = process_context
    monkeypatch.setattr(
        data_router_module,
        "process_file_content",
        lambda **kwargs: Result.success([]),
    )

    response = client.post(
        process_url(project.project_id),
        json={"file_id": "file-1"},
    )

    body = assert_api_envelope(response, is_success=False, status_code=422)

    assert body["message"] == ErrorMessage.NO_CHUNKS_GENERATED
    chunk_bl.insert_many_chunks.assert_not_awaited()


def test_process_maps_chunk_persistence_failure(
    client,
    process_context,
    project,
    assert_api_envelope,
):
    _, _, chunk_bl = process_context
    chunk_bl.insert_many_chunks.return_value = Result.failure(
        ResultError(
            code=ErrorCode.CHUNK_PERSISTENCE_FAILED,
            message=ErrorMessage.CHUNK_PERSISTENCE_FAILED,
            type=ErrorType.INTERNAL,
        )
    )

    response = client.post(
        process_url(project.project_id),
        json={"file_id": "file-1"},
    )

    body = assert_api_envelope(response, is_success=False, status_code=500)

    assert body["message"] == ErrorMessage.CHUNK_PERSISTENCE_FAILED
    assert "chunk_persistence_failed" not in response.text


def test_process_with_reset_deletes_project_chunks_before_inserting(
    client,
    process_context,
    project,
    assert_api_envelope,
):
    _, _, chunk_bl = process_context
    chunk_bl.delete_by_project_id.return_value = Result.success(0)
    chunk_bl.insert_many_chunks.side_effect = insert_all_chunks

    response = client.post(
        process_url(project.project_id),
        json={"file_id": "file-1", "do_reset": True},
    )

    assert_api_envelope(response, is_success=True, status_code=200)
    chunk_bl.delete_by_project_id.assert_awaited_once_with(project.id)

    call_names = [call[0] for call in chunk_bl.mock_calls]
    assert call_names.index("delete_by_project_id") < call_names.index(
        "insert_many_chunks"
    )


def test_process_with_reset_stops_when_project_cleanup_fails(
    client,
    process_context,
    project,
    assert_api_envelope,
):
    _, _, chunk_bl = process_context
    chunk_bl.delete_by_project_id.return_value = Result.failure(
        ResultError(
            code=ErrorCode.CHUNK_CLEANUP_FAILED,
            message="Cleanup failed.",
            type=ErrorType.INTERNAL,
        )
    )

    response = client.post(
        process_url(project.project_id),
        json={"file_id": "file-1", "do_reset": True},
    )

    body = assert_api_envelope(response, is_success=False, status_code=500)

    assert body["message"] == "Cleanup failed."
    chunk_bl.insert_many_chunks.assert_not_awaited()


def test_process_with_reset_deletes_old_chunks_even_if_insert_fails(
    client,
    process_context,
    project,
    assert_api_envelope,
):
    # This documents the current implementation: do_reset deletes *all*
    # project chunks before replacement insertion succeeds, so an insertion
    # failure leaves the project without its previous chunks.
    _, _, chunk_bl = process_context
    chunk_bl.delete_by_project_id.return_value = Result.success(3)
    chunk_bl.insert_many_chunks.return_value = Result.failure(
        ResultError(
            code=ErrorCode.CHUNK_PERSISTENCE_FAILED,
            message=ErrorMessage.CHUNK_PERSISTENCE_FAILED,
            type=ErrorType.INTERNAL,
        )
    )

    response = client.post(
        process_url(project.project_id),
        json={"file_id": "file-1", "do_reset": True},
    )

    body = assert_api_envelope(response, is_success=False, status_code=500)

    assert body["message"] == ErrorMessage.CHUNK_PERSISTENCE_FAILED
    chunk_bl.delete_by_project_id.assert_awaited_once_with(project.id)
    chunk_bl.insert_many_chunks.assert_awaited_once()
