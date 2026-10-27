from importlib import import_module

from src.dependencies.dependency_injection import (
    get_asset_business_logic,
    get_chunk_business_logic,
    get_project_business_logic,
)
from src.helpers.result_pattern import ErrorType, Result, ResultError

data_router_module = import_module("src.routes.data_router")


def test_unknown_route_returns_standardized_404(client, assert_api_envelope):
    response = client.get("/api/v1/does-not-exist")

    body = assert_api_envelope(response, is_success=False, status_code=404)

    assert body["message"] == "Not Found"


def test_request_validation_error_returns_standardized_422(
    client,
    assert_api_envelope,
    override_business_logic,
    project_bl,
    asset_bl,
    chunk_bl,
):
    override_business_logic(get_project_business_logic, project_bl)
    override_business_logic(get_asset_business_logic, asset_bl)
    override_business_logic(get_chunk_business_logic, chunk_bl)

    response = client.post("/api/v1/data/process/project-1", json={})

    body = assert_api_envelope(response, is_success=False, status_code=422)

    assert body["message"] == "Request validation failed."
    project_bl.get_project.assert_not_awaited()


def test_unhandled_exception_returns_generic_500(
    client,
    monkeypatch,
    assert_api_envelope,
    override_business_logic,
    project_bl,
    asset_bl,
    project,
):
    async def boom(file):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(
        data_router_module,
        "validate_uploaded_file",
        boom,
    )
    project_bl.get_project.return_value = Result.success(project)
    override_business_logic(get_project_business_logic, project_bl)
    override_business_logic(get_asset_business_logic, asset_bl)

    response = client.post(
        f"/api/v1/data/upload/{project.project_id}",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )

    body = assert_api_envelope(response, is_success=False, status_code=500)

    assert body["message"] == "An internal server error occurred."
    assert "secret" not in response.text


def test_result_failure_uses_status_mapping_and_message(
    client,
    assert_api_envelope,
    override_business_logic,
    project_bl,
    asset_bl,
    chunk_bl,
):
    override_business_logic(get_project_business_logic, project_bl)
    override_business_logic(get_asset_business_logic, asset_bl)
    override_business_logic(get_chunk_business_logic, chunk_bl)
    project_bl.get_project.return_value = Result.failure(
        ResultError(
            code="project_not_found",
            message="Project was not found.",
            type=ErrorType.NOT_FOUND,
        )
    )

    response = client.post(
        "/api/v1/data/process/project-1",
        json={"file_id": "file-1"},
    )

    body = assert_api_envelope(response, is_success=False, status_code=404)

    assert body["message"] == "Project was not found."
    assert "project_not_found" not in response.text
    chunk_bl.delete_by_project_id.assert_not_awaited()
