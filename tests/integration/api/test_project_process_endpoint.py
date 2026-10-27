from importlib import import_module

import pytest

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


def project_process_url(project_id):
    return f"/api/v1/data/process/project/{project_id}"


def write_asset_file(
    temp_files_dir,
    project,
    file_id,
    content,
    extension=".txt",
):
    project_dir = temp_files_dir / project.project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    path = project_dir / f"{file_id}{extension}"
    path.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)
    return path


def build_asset(make_asset, project, file_id, extension=".txt", **kwargs):
    return make_asset(
        project.id,
        file_id=file_id,
        asset_name=f"{file_id}{extension}",
        asset_type=extension,
        **kwargs,
    )


async def replace_with_generated_count(project_id, asset_id, chunks):
    return Result.success(len(chunks))


@pytest.fixture
def project_process_context(
    override_business_logic,
    project_bl,
    asset_bl,
    chunk_bl,
    project,
    temp_files_dir,
):
    override_business_logic(get_project_business_logic, project_bl)
    override_business_logic(get_asset_business_logic, asset_bl)
    override_business_logic(get_chunk_business_logic, chunk_bl)

    project_bl.get_project.return_value = Result.success(project)
    chunk_bl.replace_chunks_for_asset.side_effect = replace_with_generated_count

    return project_bl, asset_bl, chunk_bl


def test_project_process_succeeds_for_all_assets(
    client,
    project_process_context,
    project,
    make_asset,
    temp_files_dir,
    assert_api_envelope,
):
    _, asset_bl, chunk_bl = project_process_context
    first = build_asset(make_asset, project, "file-1")
    second = build_asset(make_asset, project, "file-2")
    write_asset_file(
        temp_files_dir,
        project,
        "file-1",
        "alpha bravo charlie delta echo foxtrot",
    )
    write_asset_file(
        temp_files_dir,
        project,
        "file-2",
        "golf hotel india juliet kilo lima",
    )
    asset_bl.get_all_assets_by_project_id.return_value = Result.success(
        [first, second]
    )

    response = client.post(project_process_url(project.project_id))

    body = assert_api_envelope(
        response,
        is_success=True,
        status_code=200,
        message=MessageTemplate.PROJECT_PROCESS_SUMMARY.format(
            processed_assets=2,
            total_assets=2,
            total_chunks=2,
            failed_assets=0,
        ),
    )

    data = body["data"]
    assert set(data) == {
        "project_id",
        "total_assets",
        "processed_assets",
        "failed_assets",
        "total_chunks",
        "assets",
    }
    assert data["project_id"] == project.project_id
    assert data["total_assets"] == 2
    assert data["processed_assets"] == 2
    assert data["failed_assets"] == 0
    assert data["total_chunks"] == 2

    outcomes = data["assets"]
    assert len(outcomes) == 2
    assert all(outcome["is_success"] is True for outcome in outcomes)
    assert [outcome["file_id"] for outcome in outcomes] == [
        "file-1",
        "file-2",
    ]
    assert [outcome["asset_id"] for outcome in outcomes] == [
        str(first.id),
        str(second.id),
    ]
    assert all(outcome["error_code"] is None for outcome in outcomes)
    assert all(outcome["error_message"] is None for outcome in outcomes)

    assert chunk_bl.replace_chunks_for_asset.await_count == 2
    calls = chunk_bl.replace_chunks_for_asset.await_args_list
    for call, expected_asset in zip(calls, [first, second]):
        assert call.kwargs["project_id"] == project.id
        assert call.kwargs["asset_id"] == expected_asset.id
        chunks = call.kwargs["chunks"]
        assert chunks
        assert all(chunk.chunk_project_id == project.id for chunk in chunks)
        assert all(chunk.chunk_asset_id == expected_asset.id for chunk in chunks)

    assert "alpha bravo charlie" not in response.text


def test_project_process_defaults_to_no_project_wide_reset(
    client,
    project_process_context,
    project,
    make_asset,
    temp_files_dir,
    assert_api_envelope,
):
    _, asset_bl, chunk_bl = project_process_context
    asset = build_asset(make_asset, project, "file-1")
    write_asset_file(temp_files_dir, project, "file-1", "content")
    asset_bl.get_all_assets_by_project_id.return_value = Result.success([asset])

    response = client.post(project_process_url(project.project_id))

    assert_api_envelope(response, is_success=True, status_code=200)
    chunk_bl.delete_by_project_id.assert_not_awaited()
    chunk_bl.insert_many_chunks.assert_not_awaited()


def test_project_process_forwards_default_chunk_options(
    client,
    monkeypatch,
    project_process_context,
    project,
    make_asset,
    temp_files_dir,
    assert_api_envelope,
):
    _, asset_bl, chunk_bl = project_process_context
    asset = build_asset(make_asset, project, "file-1")
    write_asset_file(temp_files_dir, project, "file-1", "content")
    asset_bl.get_all_assets_by_project_id.return_value = Result.success([asset])
    captured = []

    def fake_process(file_content, chunk_size, overlap_size):
        captured.append((chunk_size, overlap_size))
        from langchain_core.documents import Document

        return Result.success([Document(page_content="x", metadata={})])

    monkeypatch.setattr(
        data_router_module,
        "process_file_content",
        fake_process,
    )

    response = client.post(project_process_url(project.project_id))

    assert_api_envelope(response, is_success=True, status_code=200)
    assert captured == [(100, 20)]


def test_project_process_forwards_custom_chunk_options(
    client,
    monkeypatch,
    project_process_context,
    project,
    make_asset,
    temp_files_dir,
    assert_api_envelope,
):
    _, asset_bl, chunk_bl = project_process_context
    asset = build_asset(make_asset, project, "file-1")
    write_asset_file(temp_files_dir, project, "file-1", "content")
    asset_bl.get_all_assets_by_project_id.return_value = Result.success([asset])
    captured = []

    def fake_process(file_content, chunk_size, overlap_size):
        captured.append((chunk_size, overlap_size))
        from langchain_core.documents import Document

        return Result.success([Document(page_content="x", metadata={})])

    monkeypatch.setattr(
        data_router_module,
        "process_file_content",
        fake_process,
    )

    response = client.post(
        project_process_url(project.project_id),
        json={"chunk_size": 42, "overlap_size": 7},
    )

    assert_api_envelope(response, is_success=True, status_code=200)
    assert captured == [(42, 7)]


def test_project_process_returns_project_not_found(
    client,
    project_process_context,
    project,
    assert_api_envelope,
):
    project_bl, asset_bl, chunk_bl = project_process_context
    project_bl.get_project.return_value = Result.failure(
        ResultError(
            code=ErrorCode.PROJECT_NOT_FOUND,
            message=ErrorMessage.PROJECT_WAS_NOT_FOUND,
            type=ErrorType.NOT_FOUND,
        )
    )

    response = client.post(project_process_url(project.project_id))

    body = assert_api_envelope(response, is_success=False, status_code=404)

    assert body["message"] == ErrorMessage.PROJECT_WAS_NOT_FOUND
    asset_bl.get_all_assets_by_project_id.assert_not_awaited()
    chunk_bl.replace_chunks_for_asset.assert_not_awaited()


def test_project_process_rejects_project_without_id(
    client,
    project_process_context,
    project,
    assert_api_envelope,
):
    project_bl, asset_bl, chunk_bl = project_process_context
    project_bl.get_project.return_value = Result.success(
        project.model_copy(update={"id": None})
    )

    response = client.post(project_process_url(project.project_id))

    body = assert_api_envelope(response, is_success=False, status_code=500)

    assert body["message"] == ErrorMessage.PROJECT_ID_MISSING
    asset_bl.get_all_assets_by_project_id.assert_not_awaited()
    chunk_bl.replace_chunks_for_asset.assert_not_awaited()


def test_project_process_returns_asset_lookup_failure(
    client,
    project_process_context,
    project,
    assert_api_envelope,
):
    _, asset_bl, chunk_bl = project_process_context
    asset_bl.get_all_assets_by_project_id.return_value = Result.failure(
        ResultError(
            code=ErrorCode.PROJECT_NOT_FOUND,
            message=ErrorMessage.PROJECT_NOT_FOUND,
            type=ErrorType.NOT_FOUND,
        )
    )

    response = client.post(project_process_url(project.project_id))

    body = assert_api_envelope(response, is_success=False, status_code=404)

    assert body["message"] == ErrorMessage.PROJECT_NOT_FOUND
    chunk_bl.replace_chunks_for_asset.assert_not_awaited()


def test_project_process_returns_unprocessable_for_no_assets(
    client,
    project_process_context,
    project,
    assert_api_envelope,
):
    _, asset_bl, chunk_bl = project_process_context
    asset_bl.get_all_assets_by_project_id.return_value = Result.success([])

    response = client.post(project_process_url(project.project_id))

    body = assert_api_envelope(response, is_success=False, status_code=422)

    assert body["message"] == ErrorMessage.NO_ASSETS_IN_PROJECT
    assert "no_assets_in_project" not in response.text
    chunk_bl.replace_chunks_for_asset.assert_not_awaited()


def test_project_process_handles_mixed_success_and_missing_file(
    client,
    project_process_context,
    project,
    make_asset,
    temp_files_dir,
    assert_api_envelope,
):
    _, asset_bl, chunk_bl = project_process_context
    good = build_asset(make_asset, project, "file-1")
    missing = build_asset(make_asset, project, "file-2")
    write_asset_file(temp_files_dir, project, "file-1", "processable content")
    asset_bl.get_all_assets_by_project_id.return_value = Result.success(
        [good, missing]
    )

    response = client.post(project_process_url(project.project_id))

    body = assert_api_envelope(
        response,
        is_success=True,
        status_code=200,
        message=MessageTemplate.PROJECT_PROCESS_SUMMARY.format(
            processed_assets=1,
            total_assets=2,
            total_chunks=1,
            failed_assets=1,
        ),
    )

    data = body["data"]
    assert data["processed_assets"] == 1
    assert data["failed_assets"] == 1
    assert data["total_chunks"] == 1

    good_outcome, failed_outcome = data["assets"]
    assert good_outcome == {
        "asset_id": str(good.id),
        "file_id": "file-1",
        "is_success": True,
        "chunk_count": 1,
        "error_code": None,
        "error_message": None,
    }
    assert failed_outcome["asset_id"] == str(missing.id)
    assert failed_outcome["file_id"] == "file-2"
    assert failed_outcome["is_success"] is False
    assert failed_outcome["chunk_count"] == 0
    assert failed_outcome["error_code"] == ErrorCode.FILE_NOT_FOUND
    assert failed_outcome["error_message"] == MessageTemplate.FILE_NOT_FOUND.format(
        file_id="file-2",
        project_id=project.project_id,
    )

    chunk_bl.replace_chunks_for_asset.assert_awaited_once()
    assert chunk_bl.replace_chunks_for_asset.await_args.kwargs["asset_id"] == good.id


def test_project_process_returns_first_error_when_all_assets_fail(
    client,
    project_process_context,
    project,
    make_asset,
    temp_files_dir,
    assert_api_envelope,
):
    _, asset_bl, chunk_bl = project_process_context
    first = build_asset(make_asset, project, "file-1")
    second = build_asset(make_asset, project, "file-2")
    write_asset_file(temp_files_dir, project, "other", "only for directory")
    asset_bl.get_all_assets_by_project_id.return_value = Result.success(
        [first, second]
    )

    response = client.post(project_process_url(project.project_id))

    first_message = MessageTemplate.FILE_NOT_FOUND.format(
        file_id="file-1",
        project_id=project.project_id,
    )
    body = assert_api_envelope(response, is_success=False, status_code=404)

    assert body["message"] == MessageTemplate.ASSET_FAILURE_SUMMARY.format(
        message=first_message,
        remaining=1,
    )
    assert body["data"] is None
    chunk_bl.replace_chunks_for_asset.assert_not_awaited()


def test_project_process_rejects_assets_with_missing_file_metadata(
    client,
    project_process_context,
    project,
    make_asset,
    assert_api_envelope,
):
    _, asset_bl, chunk_bl = project_process_context
    missing_config = build_asset(make_asset, project, "ignored")
    missing_config = missing_config.model_copy(update={"asset_config": {}})
    blank_file_id = build_asset(make_asset, project, "ignored")
    blank_file_id = blank_file_id.model_copy(
        update={"asset_config": {"file_id": "   "}}
    )
    asset_bl.get_all_assets_by_project_id.return_value = Result.success(
        [missing_config, blank_file_id]
    )

    response = client.post(project_process_url(project.project_id))

    body = assert_api_envelope(response, is_success=False, status_code=422)

    assert body["message"] == MessageTemplate.ASSET_FAILURE_SUMMARY.format(
        message=ErrorMessage.ASSET_METADATA_MISSING,
        remaining=1,
    )
    chunk_bl.replace_chunks_for_asset.assert_not_awaited()


def test_project_process_reports_metadata_failure_without_failing_other_assets(
    client,
    project_process_context,
    project,
    make_asset,
    temp_files_dir,
    assert_api_envelope,
):
    _, asset_bl, chunk_bl = project_process_context
    good = build_asset(make_asset, project, "file-1")
    broken = build_asset(make_asset, project, "ignored")
    broken = broken.model_copy(update={"asset_config": {}})
    write_asset_file(temp_files_dir, project, "file-1", "usable content")
    asset_bl.get_all_assets_by_project_id.return_value = Result.success(
        [good, broken]
    )

    response = client.post(project_process_url(project.project_id))

    body = assert_api_envelope(
        response,
        is_success=True,
        status_code=200,
        message=MessageTemplate.PROJECT_PROCESS_SUMMARY.format(
            processed_assets=1,
            total_assets=2,
            total_chunks=1,
            failed_assets=1,
        ),
    )

    good_outcome, failed_outcome = body["data"]["assets"]
    assert good_outcome["is_success"] is True
    assert good_outcome["file_id"] == "file-1"
    assert failed_outcome == {
        "asset_id": str(broken.id),
        "file_id": None,
        "is_success": False,
        "chunk_count": 0,
        "error_code": ErrorCode.ASSET_METADATA_MISSING,
        "error_message": ErrorMessage.ASSET_METADATA_MISSING,
    }
    chunk_bl.replace_chunks_for_asset.assert_awaited_once()


def test_project_process_rejects_asset_without_id(
    client,
    project_process_context,
    project,
    make_asset,
    assert_api_envelope,
):
    _, asset_bl, chunk_bl = project_process_context
    asset = build_asset(make_asset, project, "file-1")
    asset = asset.model_copy(update={"id": None})
    asset_bl.get_all_assets_by_project_id.return_value = Result.success([asset])

    response = client.post(project_process_url(project.project_id))

    body = assert_api_envelope(response, is_success=False, status_code=500)

    assert body["message"] == ErrorMessage.INVALID_ASSET_ID
    chunk_bl.replace_chunks_for_asset.assert_not_awaited()


def test_project_process_reports_unsupported_file_type(
    client,
    project_process_context,
    project,
    make_asset,
    temp_files_dir,
    assert_api_envelope,
):
    _, asset_bl, chunk_bl = project_process_context
    asset = build_asset(
        make_asset,
        project,
        "file-1",
        extension=".docx",
    )
    write_asset_file(
        temp_files_dir,
        project,
        "file-1",
        b"docx bytes",
        extension=".docx",
    )
    asset_bl.get_all_assets_by_project_id.return_value = Result.success([asset])

    response = client.post(project_process_url(project.project_id))

    body = assert_api_envelope(response, is_success=False, status_code=400)

    assert body["message"] == MessageTemplate.UNSUPPORTED_FILE_TYPE.format(
        extension=".docx"
    )
    chunk_bl.replace_chunks_for_asset.assert_not_awaited()


def test_project_process_reports_chunk_splitting_failure(
    client,
    monkeypatch,
    project_process_context,
    project,
    make_asset,
    temp_files_dir,
    assert_api_envelope,
):
    _, asset_bl, chunk_bl = project_process_context
    asset = build_asset(make_asset, project, "file-1")
    write_asset_file(temp_files_dir, project, "file-1", "content")
    asset_bl.get_all_assets_by_project_id.return_value = Result.success([asset])
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

    response = client.post(project_process_url(project.project_id))

    body = assert_api_envelope(response, is_success=False, status_code=400)

    assert body["message"] == ErrorMessage.INVALID_CHUNK_CONFIGURATION
    chunk_bl.replace_chunks_for_asset.assert_not_awaited()


def test_project_process_reports_persistence_failure(
    client,
    project_process_context,
    project,
    make_asset,
    temp_files_dir,
    assert_api_envelope,
):
    _, asset_bl, chunk_bl = project_process_context
    first = build_asset(make_asset, project, "file-1")
    second = build_asset(make_asset, project, "file-2")
    write_asset_file(temp_files_dir, project, "file-1", "one")
    write_asset_file(temp_files_dir, project, "file-2", "two")
    asset_bl.get_all_assets_by_project_id.return_value = Result.success(
        [first, second]
    )
    chunk_bl.replace_chunks_for_asset.side_effect = None
    chunk_bl.replace_chunks_for_asset.return_value = Result.failure(
        ResultError(
            code=ErrorCode.CHUNK_PERSISTENCE_FAILED,
            message=ErrorMessage.CHUNK_PERSISTENCE_FAILED,
            type=ErrorType.INTERNAL,
        )
    )

    response = client.post(project_process_url(project.project_id))

    body = assert_api_envelope(response, is_success=False, status_code=500)

    assert body["message"] == MessageTemplate.ASSET_FAILURE_SUMMARY.format(
        message=ErrorMessage.CHUNK_PERSISTENCE_FAILED,
        remaining=1,
    )
    assert chunk_bl.replace_chunks_for_asset.await_count == 2


@pytest.mark.parametrize(
    "payload",
    [
        {"chunk_size": 0},
        {"overlap_size": -1},
        {"chunk_size": 10, "overlap_size": 10},
    ],
)
def test_project_process_rejects_invalid_options(
    client,
    project_process_context,
    project,
    payload,
    assert_api_envelope,
):
    project_bl, asset_bl, chunk_bl = project_process_context

    response = client.post(
        project_process_url(project.project_id),
        json=payload,
    )

    body = assert_api_envelope(response, is_success=False, status_code=422)

    assert body["message"] == ErrorMessage.REQUEST_VALIDATION_FAILED
    project_bl.get_project.assert_not_awaited()
    asset_bl.get_all_assets_by_project_id.assert_not_awaited()
    chunk_bl.replace_chunks_for_asset.assert_not_awaited()
