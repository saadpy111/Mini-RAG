import asyncio
import re
from pathlib import Path

from src.helpers.result_pattern import ErrorType
from src.services import file_service


def test_upload_file_saves_file_in_project_directory(
    temp_files_dir,
    make_upload_file,
):
    upload = make_upload_file(content=b"hello world")

    result = asyncio.run(file_service.upload_file("project-1", upload))

    assert result.is_success is True
    dto = result.value
    assert dto.original_filename == "notes.txt"
    assert re.fullmatch(r"[0-9a-f]{32}", dto.file_id)
    assert dto.stored_filename == f"{dto.file_id}.txt"

    expected_path = temp_files_dir / "project-1" / dto.stored_filename
    assert Path(dto.file_path) == expected_path
    assert expected_path.read_bytes() == b"hello world"
    assert upload.file.closed is True


def test_upload_file_preserves_original_filename_and_lowercases_extension(
    temp_files_dir,
    make_upload_file,
):
    upload = make_upload_file(filename="REPORT.PDF", content=b"pdf-ish")

    result = asyncio.run(file_service.upload_file("project-1", upload))

    assert result.is_success is True
    dto = result.value
    assert dto.original_filename == "REPORT.PDF"
    assert dto.stored_filename.endswith(".pdf")
    assert Path(dto.file_path).suffix == ".pdf"


def test_upload_file_accepts_empty_content(temp_files_dir, make_upload_file):
    upload = make_upload_file(content=b"")

    result = asyncio.run(file_service.upload_file("project-1", upload))

    assert result.is_success is True
    assert Path(result.value.file_path).read_bytes() == b""


def test_upload_file_generates_unique_ids(temp_files_dir, make_upload_file):
    first = asyncio.run(
        file_service.upload_file("project-1", make_upload_file(content=b"one"))
    )
    second = asyncio.run(
        file_service.upload_file("project-1", make_upload_file(content=b"two"))
    )

    assert first.is_success is True
    assert second.is_success is True
    assert first.value.file_id != second.value.file_id
    assert first.value.stored_filename != second.value.stored_filename


def test_upload_file_creates_nested_project_directory(
    temp_files_dir,
    make_upload_file,
):
    assert not (temp_files_dir / "project-1").exists()

    result = asyncio.run(
        file_service.upload_file("project-1", make_upload_file())
    )

    assert result.is_success is True
    assert (temp_files_dir / "project-1").is_dir()


def test_upload_file_rejects_invalid_project_id(
    temp_files_dir,
    make_upload_file,
):
    upload = make_upload_file()

    result = asyncio.run(file_service.upload_file("../escape", upload))

    assert result.is_success is False
    assert result.error.code == "invalid_project_id"
    assert result.error.type is ErrorType.VALIDATION
    assert upload.file.closed is True
    assert not temp_files_dir.exists()


def test_upload_file_returns_failure_on_storage_error(
    temp_files_dir,
    make_upload_file,
):
    temp_files_dir.mkdir(parents=True)
    (temp_files_dir / "project-1").write_text("not a directory")
    upload = make_upload_file()

    result = asyncio.run(file_service.upload_file("project-1", upload))

    assert result.is_success is False
    assert result.error.code == "file_storage_error"
    assert result.error.type is ErrorType.INTERNAL
    assert upload.file.closed is True


def test_upload_file_cleans_up_partial_file_on_write_failure(
    monkeypatch,
    temp_files_dir,
    make_upload_file,
):
    original_open = Path.open

    def failing_open(self, mode="r", *args, **kwargs):
        if "w" in mode:
            partial = original_open(self, mode, *args, **kwargs)
            partial.write(b"partial")
            partial.close()
            raise OSError("disk full")
        return original_open(self, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", failing_open)
    upload = make_upload_file(content=b"hello")

    result = asyncio.run(file_service.upload_file("project-1", upload))

    assert result.is_success is False
    assert result.error.code == "file_storage_error"
    assert result.error.type is ErrorType.INTERNAL
    assert upload.file.closed is True
    project_dir = temp_files_dir / "project-1"
    assert project_dir.is_dir()
    assert list(project_dir.iterdir()) == []


def test_upload_file_reads_content_in_chunks(
    monkeypatch,
    temp_files_dir,
    make_upload_file,
):
    monkeypatch.setattr(file_service, "CHUNK_SIZE", 3)
    content = b"abcdefghij"
    upload = make_upload_file(content=content)

    result = asyncio.run(file_service.upload_file("project-1", upload))

    assert result.is_success is True
    assert Path(result.value.file_path).read_bytes() == content
