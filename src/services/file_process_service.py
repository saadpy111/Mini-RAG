from pathlib import Path

from langchain_community.document_loaders import PyMuPDFLoader, TextLoader
from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pymupdf import FileDataError

from src.constants import ErrorCode, ErrorMessage, MessageTemplate
from src.enums import ProcessingEnum
from src.helpers.result_pattern import ErrorType, Result, ResultError
from src.services.project_service import get_project_path


from pathlib import Path, PureWindowsPath


def _validate_file_id(file_id: str) -> ResultError | None:
    if (
        not file_id
        or file_id in {".", ".."}
        or Path(file_id).name != file_id
        or PureWindowsPath(file_id).name != file_id
    ):
        return ResultError(
            code=ErrorCode.INVALID_FILE_ID,
            message=ErrorMessage.INVALID_FILE_ID,
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
                code=ErrorCode.FILE_LOOKUP_ERROR,
                message=ErrorMessage.FILE_LOOKUP_ERROR,
                type=ErrorType.INTERNAL,
            )
        )

    return Result.failure(
        ResultError(
            code=ErrorCode.FILE_NOT_FOUND,
            message=MessageTemplate.FILE_NOT_FOUND.format(
                file_id=file_id,
                project_id=project_id,
            ),
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
            code=ErrorCode.UNSUPPORTED_FILE_TYPE,
            message=MessageTemplate.UNSUPPORTED_FILE_TYPE.format(
                extension=extension,
            ),
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
                code=ErrorCode.INVALID_FILE_CONTENT,
                message=ErrorMessage.INVALID_FILE_CONTENT_PARSED,
                type=ErrorType.UNPROCESSABLE,
            )
        )
    except (RuntimeError, ValueError):
        return Result.failure(
            ResultError(
                code=ErrorCode.INVALID_FILE_CONTENT,
                message=ErrorMessage.INVALID_FILE_CONTENT_PROCESSED,
                type=ErrorType.UNPROCESSABLE,
            )
        )
    except OSError:
        return Result.failure(
            ResultError(
                code=ErrorCode.FILE_READ_ERROR,
                message=ErrorMessage.FILE_READ_ERROR,
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
                code=ErrorCode.EMPTY_DOCUMENT_CONTENT,
                message=ErrorMessage.EMPTY_DOCUMENT_CONTENT,
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
                code=ErrorCode.INVALID_CHUNK_SIZE,
                message=ErrorMessage.INVALID_CHUNK_SIZE,
                type=ErrorType.VALIDATION,
            )
        )

    if overlap_size < 0:
        return Result.failure(
            ResultError(
                code=ErrorCode.INVALID_OVERLAP_SIZE,
                message=ErrorMessage.INVALID_OVERLAP_SIZE,
                type=ErrorType.VALIDATION,
            )
        )

    if overlap_size >= chunk_size:
        return Result.failure(
            ResultError(
                code=ErrorCode.INVALID_CHUNK_CONFIGURATION,
                message=ErrorMessage.INVALID_CHUNK_CONFIGURATION,
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
                code=ErrorCode.EMPTY_DOCUMENT_CONTENT,
                message=ErrorMessage.NO_CONTENT_TO_PROCESS,
                type=ErrorType.UNPROCESSABLE,
            )
        )

    return Result.success(chunks)
