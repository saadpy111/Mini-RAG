import asyncio
from io import BytesIO

from starlette.datastructures import Headers, UploadFile

from src.helpers.config import settings
from src.helpers.result_pattern import ErrorType
from src.validators.file_validator import validate_uploaded_file


def make_upload(
    filename,
    content=b"data",
    content_type="text/plain",
):
    return UploadFile(
        file=BytesIO(content),
        size=len(content),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


def test_valid_file_returns_success():
    upload = make_upload("notes.txt")

    result = asyncio.run(validate_uploaded_file(upload))

    assert result.is_success is True
    assert result.value == ".txt"
    assert upload.file.tell() == 0


def test_missing_filename_fails_validation():
    upload = make_upload(None)

    result = asyncio.run(validate_uploaded_file(upload))

    assert result.is_success is False
    assert result.error.code == "missing_filename"
    assert result.error.type is ErrorType.VALIDATION


def test_unsupported_extension_fails_validation():
    upload = make_upload("malware.exe")

    result = asyncio.run(validate_uploaded_file(upload))

    assert result.is_success is False
    assert result.error.code == "unsupported_file_type"
    assert result.error.type is ErrorType.VALIDATION


def test_file_too_large_fails_with_payload_too_large(monkeypatch):
    monkeypatch.setattr(settings, "file_max_size", 1)
    upload = make_upload("big.txt", content=b"a" * (1024 * 1024 + 1))

    result = asyncio.run(validate_uploaded_file(upload))

    assert result.is_success is False
    assert result.error.code == "file_too_large"
    assert result.error.type is ErrorType.PAYLOAD_TOO_LARGE
