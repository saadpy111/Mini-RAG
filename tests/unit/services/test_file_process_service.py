import asyncio
from pathlib import Path

import pymupdf
import pytest
from langchain_community.document_loaders import PyMuPDFLoader, TextLoader
from langchain_core.documents import Document

from src.helpers.result_pattern import ErrorType, Result
from src.services import file_process_service


def write_project_file(files_dir, project_id, file_id, suffix, content):
    project_dir = files_dir / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    path = project_dir / f"{file_id}{suffix}"
    path.write_bytes(content)
    return path


def write_pdf(files_dir, project_id, file_id, text):
    path = files_dir / project_id / f"{file_id}.pdf"
    path.parent.mkdir(parents=True, exist_ok=True)

    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    document.save(str(path))
    document.close()
    return path


class StaticLoader:
    def __init__(self, documents=None, error=None):
        self.documents = documents or []
        self.error = error

    def load(self):
        if self.error is not None:
            raise self.error
        return self.documents


def use_loader(monkeypatch, loader):
    monkeypatch.setattr(
        file_process_service,
        "get_file_loader",
        lambda project_id, file_id: Result.success(loader),
    )


def test_get_file_path_returns_matching_file(temp_files_dir):
    path = write_project_file(
        temp_files_dir,
        "project-1",
        "file-1",
        ".txt",
        b"content",
    )

    result = file_process_service.get_file_path("project-1", "file-1")

    assert result.is_success is True
    assert result.value == path


@pytest.mark.parametrize(
    "file_id",
    ["", ".", "..", "../escape", "sub/file", "sub\\file"],
)
def test_get_file_path_rejects_invalid_file_ids(temp_files_dir, file_id):
    result = file_process_service.get_file_path("project-1", file_id)

    assert result.is_success is False
    assert result.error.code == "invalid_file_id"
    assert result.error.type is ErrorType.VALIDATION


def test_get_file_path_returns_project_not_found(temp_files_dir):
    result = file_process_service.get_file_path("missing", "file-1")

    assert result.is_success is False
    assert result.error.code == "project_not_found"
    assert result.error.type is ErrorType.NOT_FOUND


def test_get_file_path_returns_file_not_found(temp_files_dir):
    (temp_files_dir / "project-1").mkdir(parents=True)

    result = file_process_service.get_file_path("project-1", "missing")

    assert result.is_success is False
    assert result.error.code == "file_not_found"
    assert result.error.type is ErrorType.NOT_FOUND
    assert "missing" in result.error.message


def test_get_file_path_maps_iteration_failure_to_lookup_error(
    monkeypatch,
    temp_files_dir,
):
    (temp_files_dir / "project-1").mkdir(parents=True)

    def broken_iterdir(self):
        raise OSError("permission denied")

    monkeypatch.setattr(Path, "iterdir", broken_iterdir)

    result = file_process_service.get_file_path("project-1", "file-1")

    assert result.is_success is False
    assert result.error.code == "file_lookup_error"
    assert result.error.type is ErrorType.INTERNAL


def test_get_file_loader_selects_text_loader(temp_files_dir):
    write_project_file(temp_files_dir, "project-1", "file-1", ".txt", b"text")

    result = file_process_service.get_file_loader("project-1", "file-1")

    assert result.is_success is True
    assert isinstance(result.value, TextLoader)


def test_get_file_loader_selects_pdf_loader(temp_files_dir):
    write_pdf(temp_files_dir, "project-1", "file-1", "PDF text")

    result = file_process_service.get_file_loader("project-1", "file-1")

    assert result.is_success is True
    assert isinstance(result.value, PyMuPDFLoader)


def test_get_file_loader_rejects_unsupported_extension(temp_files_dir):
    write_project_file(temp_files_dir, "project-1", "file-1", ".docx", b"text")

    result = file_process_service.get_file_loader("project-1", "file-1")

    assert result.is_success is False
    assert result.error.code == "unsupported_file_type"
    assert result.error.type is ErrorType.VALIDATION
    assert ".docx" in result.error.message


def test_get_file_content_reads_text_file(temp_files_dir):
    write_project_file(
        temp_files_dir,
        "project-1",
        "file-1",
        ".txt",
        b"Hello from a text file.",
    )

    result = file_process_service.get_file_content("project-1", "file-1")

    assert result.is_success is True
    assert len(result.value) == 1
    assert "Hello from a text file." in result.value[0].page_content
    assert result.value[0].metadata["source"].endswith("file-1.txt")


def test_get_file_content_reads_pdf_file(temp_files_dir):
    write_pdf(temp_files_dir, "project-1", "file-1", "Hello from a PDF file.")

    result = file_process_service.get_file_content("project-1", "file-1")

    assert result.is_success is True
    assert any(
        "Hello from a PDF file." in document.page_content
        for document in result.value
    )


def test_get_file_content_maps_malformed_pdf_to_unprocessable(temp_files_dir):
    write_project_file(
        temp_files_dir,
        "project-1",
        "broken",
        ".pdf",
        b"this is not a pdf",
    )

    result = file_process_service.get_file_content("project-1", "broken")

    assert result.is_success is False
    assert result.error.code == "invalid_file_content"
    assert result.error.type is ErrorType.UNPROCESSABLE


def test_get_file_content_filters_blank_documents(monkeypatch):
    loader = StaticLoader(
        documents=[
            Document(page_content="", metadata={"page": 0}),
            Document(page_content="   ", metadata={"page": 1}),
            Document(page_content="usable", metadata={"page": 2}),
        ]
    )
    use_loader(monkeypatch, loader)

    result = file_process_service.get_file_content("project-1", "file-1")

    assert result.is_success is True
    assert [document.page_content for document in result.value] == ["usable"]


def test_get_file_content_rejects_empty_extracted_content(monkeypatch):
    use_loader(
        monkeypatch,
        StaticLoader(documents=[Document(page_content="  ", metadata={})]),
    )

    result = file_process_service.get_file_content("project-1", "file-1")

    assert result.is_success is False
    assert result.error.code == "empty_document_content"
    assert result.error.type is ErrorType.UNPROCESSABLE


@pytest.mark.parametrize(
    ("error", "expected_code", "expected_type"),
    [
        (RuntimeError("bad data"), "invalid_file_content", ErrorType.UNPROCESSABLE),
        (ValueError("bad data"), "invalid_file_content", ErrorType.UNPROCESSABLE),
        (OSError("cannot read"), "file_read_error", ErrorType.INTERNAL),
    ],
)
def test_get_file_content_maps_loader_errors(
    monkeypatch,
    error,
    expected_code,
    expected_type,
):
    use_loader(monkeypatch, StaticLoader(error=error))

    result = file_process_service.get_file_content("project-1", "file-1")

    assert result.is_success is False
    assert result.error.code == expected_code
    assert result.error.type is expected_type


def test_process_file_content_splits_and_preserves_metadata():
    text = "abcdefghij" * 10
    metadata = {"source": "file-1.txt", "page": 1}

    result = file_process_service.process_file_content(
        [Document(page_content=text, metadata=metadata)],
        chunk_size=20,
        overlap_size=5,
    )

    assert result.is_success is True
    chunks = result.value
    assert len(chunks) > 1
    assert all(len(chunk.page_content) <= 20 for chunk in chunks)
    assert all(chunk.metadata == metadata for chunk in chunks)
    assert chunks[0].page_content == text[:20]


def test_process_file_content_preserves_document_order_and_metadata():
    documents = [
        Document(page_content="first", metadata={"source": "a.txt"}),
        Document(page_content="second", metadata={"source": "b.txt"}),
    ]

    result = file_process_service.process_file_content(
        documents,
        chunk_size=100,
        overlap_size=0,
    )

    assert result.is_success is True
    assert [chunk.page_content for chunk in result.value] == ["first", "second"]
    assert [chunk.metadata["source"] for chunk in result.value] == ["a.txt", "b.txt"]


def test_process_file_content_rejects_empty_document_list():
    result = file_process_service.process_file_content([])

    assert result.is_success is False
    assert result.error.code == "empty_document_content"
    assert result.error.type is ErrorType.UNPROCESSABLE


def test_process_file_content_rejects_empty_page_content():
    result = file_process_service.process_file_content(
        [Document(page_content="   ", metadata={})]
    )

    assert result.is_success is False
    assert result.error.code == "empty_document_content"
    assert result.error.type is ErrorType.UNPROCESSABLE


@pytest.mark.parametrize("chunk_size", [0, -1])
def test_process_file_content_rejects_invalid_chunk_size(chunk_size):
    result = file_process_service.process_file_content(
        [Document(page_content="content", metadata={})],
        chunk_size=chunk_size,
    )

    assert result.is_success is False
    assert result.error.code == "invalid_chunk_size"
    assert result.error.type is ErrorType.VALIDATION


def test_process_file_content_rejects_negative_overlap():
    result = file_process_service.process_file_content(
        [Document(page_content="content", metadata={})],
        chunk_size=10,
        overlap_size=-1,
    )

    assert result.is_success is False
    assert result.error.code == "invalid_overlap_size"
    assert result.error.type is ErrorType.VALIDATION


@pytest.mark.parametrize("overlap_size", [10, 11])
def test_process_file_content_rejects_overlap_not_smaller_than_chunk(
    overlap_size,
):
    result = file_process_service.process_file_content(
        [Document(page_content="content", metadata={})],
        chunk_size=10,
        overlap_size=overlap_size,
    )

    assert result.is_success is False
    assert result.error.code == "invalid_chunk_configuration"
    assert result.error.type is ErrorType.VALIDATION


def test_process_file_content_uses_default_configuration():
    result = file_process_service.process_file_content(
        [Document(page_content="small content", metadata={"source": "a.txt"})]
    )

    assert result.is_success is True
    assert len(result.value) == 1
    assert result.value[0].page_content == "small content"
