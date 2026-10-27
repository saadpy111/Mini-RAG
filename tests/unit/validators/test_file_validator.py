import asyncio

import pytest

from src.helpers.config import settings
from src.helpers.result_pattern import ErrorType
from src.validators.file_validator import validate_uploaded_file


@pytest.mark.parametrize(
    ("filename", "expected_extension"),
    [
        ("notes.txt", ".txt"),
        ("document.pdf", ".pdf"),
        ("report.docx", ".docx"),
        ("UPPER.TXT", ".txt"),
        ("Mixed.PdF", ".pdf"),
    ],
)
def test_valid_extensions_are_accepted(
    make_upload_file,
    filename,
    expected_extension,
):
    upload = make_upload_file(filename=filename)

    result = asyncio.run(validate_uploaded_file(upload))

    assert result.is_success is True
    assert result.value == expected_extension
    assert upload.file.tell() == 0


def test_missing_filename_fails_validation(make_upload_file):
    upload = make_upload_file(filename=None)

    result = asyncio.run(validate_uploaded_file(upload))

    assert result.is_success is False
    assert result.error.code == "missing_filename"
    assert result.error.message == "Filename is required."
    assert result.error.type is ErrorType.VALIDATION


def test_filename_without_extension_is_unsupported(make_upload_file):
    upload = make_upload_file(filename="README")

    result = asyncio.run(validate_uploaded_file(upload))

    assert result.is_success is False
    assert result.error.code == "unsupported_file_type"
    assert result.error.type is ErrorType.VALIDATION


@pytest.mark.parametrize("filename", ["malware.exe", "document.doc", "archive.tar.gz"])
def test_unsupported_extensions_fail_validation(make_upload_file, filename):
    upload = make_upload_file(filename=filename)

    result = asyncio.run(validate_uploaded_file(upload))

    assert result.is_success is False
    assert result.error.code == "unsupported_file_type"
    assert result.error.type is ErrorType.VALIDATION
    assert "Allowed types:" in result.error.message


def test_empty_file_is_accepted_by_current_contract(make_upload_file):
    upload = make_upload_file(content=b"")

    result = asyncio.run(validate_uploaded_file(upload))

    assert result.is_success is True
    assert result.value == ".txt"
    assert upload.file.tell() == 0


def test_file_too_large_fails_with_payload_too_large(monkeypatch, make_upload_file):
    monkeypatch.setattr(settings, "file_max_size", 1)
    upload = make_upload_file(content=b"a" * (1024 * 1024 + 1))

    result = asyncio.run(validate_uploaded_file(upload))

    assert result.is_success is False
    assert result.error.code == "file_too_large"
    assert result.error.type is ErrorType.PAYLOAD_TOO_LARGE
    assert "1 MB" in result.error.message
    assert upload.file.tell() == 0


def test_file_at_exact_size_limit_is_accepted(monkeypatch, make_upload_file):
    monkeypatch.setattr(settings, "file_max_size", 1)
    upload = make_upload_file(content=b"a" * (1024 * 1024))

    result = asyncio.run(validate_uploaded_file(upload))

    assert result.is_success is True
    assert upload.file.tell() == 0


def test_validation_does_not_use_content_type(make_upload_file):
    upload = make_upload_file(
        filename="notes.txt",
        content_type="application/octet-stream",
    )

    result = asyncio.run(validate_uploaded_file(upload))

    assert result.is_success is True
    assert result.value == ".txt"
