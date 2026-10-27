from pathlib import Path
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
    get_project_business_logic,
)
from src.dtos import UploadFileDTO
from src.helpers.config import settings
from src.helpers.result_pattern import ErrorType, Result, ResultError

data_router_module = import_module("src.routes.data_router")


@pytest.fixture
def upload_context(
    override_business_logic,
    project_bl,
    asset_bl,
    project,
):
    override_business_logic(get_project_business_logic, project_bl)
    override_business_logic(get_asset_business_logic, asset_bl)
    project_bl.get_project.return_value = Result.success(project)
    return project_bl, asset_bl


def upload_url(project_id):
    return f"/api/v1/data/upload/{project_id}"


def post_file(client, project_id, filename="notes.txt", content=b"hello"):
    return client.post(
        upload_url(project_id),
        files={"file": (filename, content, "text/plain")},
    )


def test_upload_success_returns_created_and_dto(
    client,
    upload_context,
    project,
    asset,
    temp_files_dir,
    assert_api_envelope,
):
    _, asset_bl = upload_context
    asset_bl.create_asset.return_value = Result.success(asset)

    response = post_file(client, project.project_id, content=b"hello world")

    body = assert_api_envelope(
        response,
        is_success=True,
        status_code=201,
        message=SuccessMessage.FILE_UPLOADED,
    )

    data = body["data"]
    assert set(data) == {
        "original_filename",
        "stored_filename",
        "file_id",
        "file_path",
    }
    assert data["original_filename"] == "notes.txt"
    assert data["stored_filename"].endswith(".txt")
    assert data["stored_filename"].startswith(data["file_id"])

    stored_path = Path(data["file_path"])
    assert stored_path.parent == temp_files_dir / project.project_id
    assert stored_path.read_bytes() == b"hello world"

    asset_arg = asset_bl.create_asset.await_args.args[0]
    assert asset_arg.asset_project_id == project.id
    assert asset_arg.asset_type == ".txt"
    assert asset_arg.asset_name == data["stored_filename"]
    assert asset_arg.asset_size == len(b"hello world")
    assert asset_arg.asset_config["file_id"] == data["file_id"]
    assert asset_arg.asset_config["original_filename"] == "notes.txt"
    assert asset_arg.asset_config["file_path"] == data["file_path"]


def test_upload_creates_project_when_missing(
    client,
    upload_context,
    project,
    asset,
    temp_files_dir,
    assert_api_envelope,
):
    project_bl, asset_bl = upload_context
    project_bl.get_project.return_value = Result.failure(
        ResultError(
            code=ErrorCode.PROJECT_NOT_FOUND,
            message=ErrorMessage.PROJECT_WAS_NOT_FOUND,
            type=ErrorType.NOT_FOUND,
        )
    )
    project_bl.create_project.return_value = Result.success(project)
    asset_bl.create_asset.return_value = Result.success(asset)

    response = post_file(client, project.project_id)

    assert_api_envelope(response, is_success=True, status_code=201)

    created_project = project_bl.create_project.await_args.args[0]
    assert created_project.project_id == project.project_id
    assert (temp_files_dir / project.project_id).is_dir()


def test_upload_propagates_project_lookup_failure(
    client,
    upload_context,
    project,
    assert_api_envelope,
):
    project_bl, asset_bl = upload_context
    project_bl.get_project.return_value = Result.failure(
        ResultError(
            code="project_lookup_failed",
            message="Project lookup failed.",
            type=ErrorType.INTERNAL,
        )
    )

    response = post_file(client, project.project_id)

    body = assert_api_envelope(response, is_success=False, status_code=500)

    assert body["message"] == "Project lookup failed."
    project_bl.create_project.assert_not_awaited()
    asset_bl.create_asset.assert_not_awaited()


def test_upload_rejects_unsupported_extension(
    client,
    upload_context,
    project,
    temp_files_dir,
    assert_api_envelope,
):
    _, asset_bl = upload_context

    response = post_file(client, project.project_id, filename="malware.exe")

    body = assert_api_envelope(response, is_success=False, status_code=400)

    expected_message = MessageTemplate.ALLOWED_FILE_TYPES.format(
        allowed_types=", ".join(settings.file_allowed_types)
    )
    assert body["message"] == expected_message
    assert "unsupported_file_type" not in response.text
    asset_bl.create_asset.assert_not_awaited()
    assert not (temp_files_dir / project.project_id).exists()


def test_upload_rejects_oversized_file(
    client,
    monkeypatch,
    upload_context,
    project,
    assert_api_envelope,
):
    _, asset_bl = upload_context
    monkeypatch.setattr(settings, "file_max_size", 1)

    response = post_file(
        client,
        project.project_id,
        content=b"a" * (1024 * 1024 + 1),
    )

    body = assert_api_envelope(response, is_success=False, status_code=413)

    assert body["message"] == "File size exceeds the limit of 1 MB."
    asset_bl.create_asset.assert_not_awaited()


def test_upload_without_file_returns_standardized_422(
    client,
    upload_context,
    project,
    assert_api_envelope,
):
    _, asset_bl = upload_context

    response = client.post(upload_url(project.project_id))

    body = assert_api_envelope(response, is_success=False, status_code=422)

    assert body["message"] == "Request validation failed."
    asset_bl.create_asset.assert_not_awaited()


def test_upload_storage_failure_returns_500(
    client,
    upload_context,
    project,
    temp_files_dir,
    assert_api_envelope,
):
    _, asset_bl = upload_context
    temp_files_dir.mkdir(parents=True)
    (temp_files_dir / project.project_id).write_text("not a directory")

    response = post_file(client, project.project_id)

    body = assert_api_envelope(response, is_success=False, status_code=500)

    assert body["message"] == ErrorMessage.FILE_STORAGE_ERROR
    asset_bl.create_asset.assert_not_awaited()


def test_upload_size_lookup_failure_returns_500(
    client,
    monkeypatch,
    upload_context,
    project,
    tmp_path,
    assert_api_envelope,
):
    _, asset_bl = upload_context

    async def fake_upload(project_id, file):
        await file.close()
        return Result.success(
            UploadFileDTO(
                original_filename="notes.txt",
                stored_filename="missing.txt",
                file_id="missing",
                file_path=str(tmp_path / "missing.txt"),
            )
        )

    monkeypatch.setattr(data_router_module, "upload_file", fake_upload)

    response = post_file(client, project.project_id)

    body = assert_api_envelope(response, is_success=False, status_code=500)

    assert body["message"] == ErrorMessage.UPLOADED_FILE_SIZE_UNAVAILABLE
    asset_bl.create_asset.assert_not_awaited()


def test_upload_asset_persistence_failure_keeps_file_on_disk(
    client,
    upload_context,
    project,
    temp_files_dir,
    assert_api_envelope,
):
    _, asset_bl = upload_context
    asset_bl.create_asset.return_value = Result.failure(
        ResultError(
            code="asset_persistence_failed",
            message="Asset metadata could not be saved.",
            type=ErrorType.INTERNAL,
        )
    )

    response = post_file(client, project.project_id, content=b"stored")

    body = assert_api_envelope(response, is_success=False, status_code=500)

    assert body["message"] == "Asset metadata could not be saved."
    # This documents the current implementation: the physical file is not
    # removed when metadata persistence fails.
    project_files = list((temp_files_dir / project.project_id).iterdir())
    assert len(project_files) == 1
    assert project_files[0].read_bytes() == b"stored"


def test_upload_empty_file_is_accepted(
    client,
    upload_context,
    project,
    asset,
    temp_files_dir,
    assert_api_envelope,
):
    _, asset_bl = upload_context
    asset_bl.create_asset.return_value = Result.success(asset)

    response = post_file(client, project.project_id, content=b"")

    assert_api_envelope(response, is_success=True, status_code=201)
    asset_arg = asset_bl.create_asset.await_args.args[0]
    assert asset_arg.asset_size == 0


def test_upload_response_does_not_expose_sensitive_configuration(
    client,
    upload_context,
    project,
    asset,
    temp_files_dir,
    assert_api_envelope,
):
    _, asset_bl = upload_context
    asset_bl.create_asset.return_value = Result.success(asset)

    response = post_file(client, project.project_id)

    body = assert_api_envelope(response, is_success=True, status_code=201)
    assert set(body["data"]) == {
        "original_filename",
        "stored_filename",
        "file_id",
        "file_path",
    }

    assert settings.mongodb_uri not in response.text
    assert "MONGODB_URI" not in response.text
    assert "mongodb://" not in response.text
    openai_key = settings.openai_api_key.get_secret_value()
    if openai_key:
        assert openai_key not in response.text
