from fastapi.testclient import TestClient

import main
from src.helpers.config import settings
from src.services import file_service

client = TestClient(main.app, raise_server_exceptions=False)


def upload(filename, content, content_type="text/plain"):
    return client.post(
        "/api/v1/data/upload",
        files={"file": (filename, content, content_type)},
    )


def test_root_returns_standardized_success():
    response = client.get("/api/v1/")

    assert response.status_code == 200
    body = response.json()
    assert body["is_success"] is True
    assert body["message"]
    assert set(body["data"]) == {"APP_NAME", "APP_VERSION"}


def test_upload_returns_created(monkeypatch, tmp_path):
    monkeypatch.setattr(file_service, "UPLOAD_DIR", tmp_path)

    response = upload("notes.txt", b"hello")

    assert response.status_code == 201
    body = response.json()
    assert body["is_success"] is True
    assert body["message"] == "File uploaded successfully."
    assert body["data"]["original_filename"] == "notes.txt"


def test_upload_rejects_unsupported_type():
    response = upload("malware.exe", b"x")

    assert response.status_code == 400
    body = response.json()
    assert body["is_success"] is False
    assert body["data"] is None


def test_upload_rejects_large_file(monkeypatch):
    monkeypatch.setattr(settings, "file_max_size", 1)

    response = upload("big.txt", b"a" * (1024 * 1024 + 1))

    assert response.status_code == 413
    body = response.json()
    assert body["is_success"] is False
    assert body["data"] is None


def test_upload_without_file_returns_standardized_422():
    response = client.post("/api/v1/data/upload")

    assert response.status_code == 422
    body = response.json()
    assert body["is_success"] is False
    assert body["data"] is None


def test_upload_storage_failure_returns_envelope(monkeypatch, tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory")
    monkeypatch.setattr(file_service, "UPLOAD_DIR", blocker / "files")

    response = upload("notes.txt", b"hi")

    assert response.status_code == 500
    body = response.json()
    assert body["is_success"] is False
    assert body["data"] is None


def test_unexpected_error_returns_generic_500(monkeypatch):
    async def boom(file):
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(
        "src.controllers.DataController.validate_uploaded_file",
        boom,
    )

    response = upload("notes.txt", b"hi")

    assert response.status_code == 500
    body = response.json()
    assert body["is_success"] is False
    assert body["message"] == "An internal server error occurred."
    assert "secret" not in response.text


def test_success_and_failure_share_response_schema(monkeypatch, tmp_path):
    monkeypatch.setattr(file_service, "UPLOAD_DIR", tmp_path)

    success = upload("notes.txt", b"hi").json()
    failure = upload("bad.exe", b"hi").json()

    for body in (success, failure):
        assert set(body) == {"is_success", "message", "data"}
