from fastapi import APIRouter, File, UploadFile, status
from fastapi.responses import JSONResponse

from src.api import to_http_response
from src.dtos import (
    ApiResponse,
    ProcessedChunkDTO,
    ProcessRequest,
    UploadFileDTO,
)
from src.helpers.result_pattern import Result
from src.services.file_process_service import get_file_content, process_file_content
from src.services.file_service import upload_file
from src.validators.file_validator import validate_uploaded_file
from src.validators.process_validator import validate_process_request

data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["Data"],
)


@data_router.post(
    "/upload/{project_id}",
    response_model=ApiResponse[UploadFileDTO],
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ApiResponse[None]},
        status.HTTP_413_CONTENT_TOO_LARGE: {"model": ApiResponse[None]},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ApiResponse[None]},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ApiResponse[None]},
    },
)
async def upload_document(
    project_id: str,
    file: UploadFile = File(...),
) -> JSONResponse:
    validation_result = await validate_uploaded_file(file)
    if not validation_result.is_success:
        return to_http_response(validation_result)

    result = await upload_file(project_id, file)

    return to_http_response(
        result,
        success_status_code=status.HTTP_201_CREATED,
        success_message="File uploaded successfully.",
    )


@data_router.post(
    "/process/{project_id}",
    response_model=ApiResponse[list[ProcessedChunkDTO]],
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ApiResponse[None]},
        status.HTTP_404_NOT_FOUND: {"model": ApiResponse[None]},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ApiResponse[None]},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ApiResponse[None]},
    },
)
async def process_document(
    project_id: str,
    process_request: ProcessRequest,
) -> JSONResponse:
    request_validation_result = validate_process_request(process_request)
    if not request_validation_result.is_success:
        return to_http_response(request_validation_result)

    file_content_result = get_file_content(
        project_id=project_id,
        file_id=process_request.file_id,
    )
    if not file_content_result.is_success:
        return to_http_response(file_content_result)

    chunks_result = process_file_content(
        file_content=file_content_result.value,
        chunk_size=process_request.chunk_size,
        overlap_size=process_request.overlap_size,
    )
    if not chunks_result.is_success:
        return to_http_response(chunks_result)

    chunks = [
        ProcessedChunkDTO(
            page_content=document.page_content,
            metadata=document.metadata,
        )
        for document in chunks_result.value
    ]

    return to_http_response(
        Result.success(chunks),
        success_message="File processed successfully.",
    )
