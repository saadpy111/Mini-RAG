import asyncio
from io import BytesIO
from pathlib import Path

from starlette.datastructures import Headers, UploadFile

from src.helpers.result_pattern import ErrorType
from src.services import file_service


def make_upload(
    filename="notes.txt",
    content=b"hello",
    content_type="text/plain",
):
    return UploadFile(
        file=BytesIO(content),
        size=len(content),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


def test_upload_file_saves_file(monkeypatch, tmp_path):
    monkeypatch.setattr(file_service, "UPLOAD_DIR", tmp_path)
    upload = make_upload(content=b"hello world")

    result = asyncio.run(file_service.upload_file(upload))

    assert result.is_success is True
    dto = result.value
    assert dto.original_filename == "notes.txt"
    assert dto.stored_filename.endswith(".txt")
    assert Path(dto.file_path).read_bytes() == b"hello world"


def test_upload_file_returns_failure_on_storage_error(monkeypatch, tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory")
    monkeypatch.setattr(file_service, "UPLOAD_DIR", blocker / "files")
    upload = make_upload()

    result = asyncio.run(file_service.upload_file(upload))

    assert result.is_success is False
    assert result.error.code == "file_storage_error"
    assert result.error.type is ErrorType.INTERNAL
