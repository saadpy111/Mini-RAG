from pathlib import Path

from langchain_community.document_loaders import PyMuPDFLoader, TextLoader
from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pymupdf import FileDataError

from src.enums import ProcessingEnum
from src.helpers.result_pattern import ErrorType, Result, ResultError
from src.services.project_service import get_project_path


def _validate_file_id(file_id: str) -> ResultError | None:
    if (
        not file_id
        or file_id in {".", ".."}
        or Path(file_id).name != file_id
    ):
        return ResultError(
            code="invalid_file_id",
            message="Invalid file ID.",
            type=ErrorType.VALIDATION,
        )

    return None


def get_file_path(project_id: str, file_id: str) -> Result[Path]:
    validation_error = _validate_file_id(file_id)
    if validation_error is not None:
        return Result.failure(validation_error)

    project_path_result = get_project_path(project_id)
    if not project_path_result.is_success:
        return project_path_result

    project_path = project_path_result.value

    try:
        for file_path in project_path.iterdir():
            if file_path.is_file() and file_path.stem == file_id:
                return Result.success(file_path)
    except OSError:
        return Result.failure(
            ResultError(
                code="file_lookup_error",
                message="Failed to access the project files.",
                type=ErrorType.INTERNAL,
            )
        )

    return Result.failure(
        ResultError(
            code="file_not_found",
            message=f"File '{file_id}' was not found in project '{project_id}'.",
            type=ErrorType.NOT_FOUND,
        )
    )


def get_file_loader(project_id: str, file_id: str) -> Result[BaseLoader]:
    file_path_result = get_file_path(project_id, file_id)
    if not file_path_result.is_success:
        return file_path_result

    file_path = file_path_result.value
    extension = file_path.suffix.lower()

    if extension == ProcessingEnum.TXT.value:
        return Result.success(TextLoader(str(file_path)))

    if extension == ProcessingEnum.PDF.value:
        return Result.success(PyMuPDFLoader(str(file_path)))

    return Result.failure(
        ResultError(
            code="unsupported_file_type",
            message=f"Unsupported file type: {extension}.",
            type=ErrorType.VALIDATION,
        )
    )


def get_file_content(project_id: str, file_id: str) -> Result[list[Document]]:
    loader_result = get_file_loader(project_id, file_id)
    if not loader_result.is_success:
        return loader_result

    try:
        documents = loader_result.value.load()
    except FileDataError:
        return Result.failure(
            ResultError(
                code="invalid_file_content",
                message="The file content could not be parsed.",
                type=ErrorType.UNPROCESSABLE,
            )
        )
    except (RuntimeError, ValueError):
        return Result.failure(
            ResultError(
                code="invalid_file_content",
                message="The file content could not be processed.",
                type=ErrorType.UNPROCESSABLE,
            )
        )
    except OSError:
        return Result.failure(
            ResultError(
                code="file_read_error",
                message="Failed to read the file content.",
                type=ErrorType.INTERNAL,
            )
        )

    documents = [
        document
        for document in documents
        if document.page_content and document.page_content.strip()
    ]

    if not documents:
        return Result.failure(
            ResultError(
                code="empty_document_content",
                message="The file does not contain any processable content.",
                type=ErrorType.UNPROCESSABLE,
            )
        )

    return Result.success(documents)


def process_file_content(
    file_content: list[Document],
    chunk_size: int = 100,
    overlap_size: int = 20,
) -> Result[list[Document]]:
    if chunk_size <= 0:
        return Result.failure(
            ResultError(
                code="invalid_chunk_size",
                message="chunk_size must be greater than zero.",
                type=ErrorType.VALIDATION,
            )
        )

    if overlap_size < 0:
        return Result.failure(
            ResultError(
                code="invalid_overlap_size",
                message="overlap_size cannot be negative.",
                type=ErrorType.VALIDATION,
            )
        )

    if overlap_size >= chunk_size:
        return Result.failure(
            ResultError(
                code="invalid_chunk_configuration",
                message="overlap_size must be smaller than chunk_size.",
                type=ErrorType.VALIDATION,
            )
        )

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap_size,
    )

    texts = [document.page_content for document in file_content]
    metadatas = [document.metadata for document in file_content]

    chunks = text_splitter.create_documents(
        texts,
        metadatas=metadatas,
    )

    if not chunks:
        return Result.failure(
            ResultError(
                code="empty_document_content",
                message="No content found to process.",
                type=ErrorType.UNPROCESSABLE,
            )
        )

    return Result.success(chunks)
