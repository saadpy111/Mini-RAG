
from bson import ObjectId
from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import JSONResponse
from typing import Annotated
from src.helpers.result_pattern import Result, ResultError, ErrorType
from src.api import to_http_response
from src.dependencies.dependency_injection import (
    get_chunk_business_logic,
    get_project_business_logic,
)
from src.dtos import (
    ApiResponse,
    ProcessedChunkDTO,
    ProcessRequest,
    UploadFileDTO,
)
from src.helpers.result_pattern import Result
from src.models.data_chunk import DataChunk
from src.models.project import Project
from src.business_logic.chunk_business_logic import ChunkBusinessLogic
from src.business_logic.project_business_logic import ProjectBusinessLogic
from src.services.file_process_service import (
    get_file_content,
    process_file_content,
)
from src.services.file_service import upload_file
from src.validators.file_validator import validate_uploaded_file
from src.validators.process_validator import validate_process_request


data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["Data"],
)

project_router = APIRouter(
    prefix="/api/v1/projects",
    tags=["Projects"],
)


ProjectBL = Annotated[
    ProjectBusinessLogic,
    Depends(get_project_business_logic),
]

ChunkBL = Annotated[
    ChunkBusinessLogic,
    Depends(get_chunk_business_logic),
]



# Project endpoints


@project_router.post(
    "",
    response_model=ApiResponse[Project],
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    project: Project,
    project_bl: ProjectBL,
) -> JSONResponse:
    result = await project_bl.create_project(project)

    return to_http_response(
        result,
        success_status_code=status.HTTP_201_CREATED,
        success_message="Project created successfully.",
    )


@project_router.get(
    "/{project_id}",
    response_model=ApiResponse[Project],
)
async def get_project(
    project_id: str,
    project_bl: ProjectBL,
) -> JSONResponse:
    result = await project_bl.get_project(project_id)

    return to_http_response(result)



# Upload endpoint


@data_router.post(
    "/upload/{project_id}",
    response_model=ApiResponse[UploadFileDTO],
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    project_id: str,
    file: UploadFile = File(...),
    project_bl: ProjectBL = None,
) -> JSONResponse:
    project_result = await project_bl.get_project(project_id)

    if project_result.error.type != ErrorType.NOT_FOUND:
            return to_http_response(project_result)

    create_result = await project_bl.create_project(
            Project(project_id=project_id)
        )

    if not create_result.is_success:
            return to_http_response(create_result)
    validation_result = await validate_uploaded_file(file)

    if not validation_result.is_success:
        return to_http_response(validation_result)

    result = await upload_file(project_id, file)

    return to_http_response(
        result,
        success_status_code=status.HTTP_201_CREATED,
        success_message="File uploaded successfully.",
    )



# Process and persist chunks


@data_router.post(
    "/process/{project_id}",
    response_model=ApiResponse[list[ProcessedChunkDTO]],
)
async def process_document(
    project_id: str,
    process_request: ProcessRequest,
    project_bl: ProjectBL,
    chunk_bl: ChunkBL,
) -> JSONResponse:
    request_result = validate_process_request(process_request)

    if not request_result.is_success:
        return to_http_response(request_result)

    project_result = await project_bl.get_project(project_id)

    if not project_result.is_success:
        return to_http_response(project_result)

    project = project_result.value

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

    documents = chunks_result.value

    if not documents:
     return to_http_response(
        Result.failure(
            ResultError(
                code="no_chunks_generated",
                message="No chunks were generated from the file.",
                type=ErrorType.UNPROCESSABLE,
            )
        )
    )
    if process_request.do_reset:
       delete_result = await chunk_bl.delete_by_project_id(project.id)
       if not delete_result.is_success:
          return to_http_response(delete_result)
    
    data_chunks = [
        DataChunk(
            chunk_text=document.page_content,
            chunk_metadata=document.metadata,
            chunk_order=index,
            chunk_project_id=project.id,
        )
        for index, document in enumerate(documents, start=1)
    ]

    save_result = await chunk_bl.insert_many_chunks(data_chunks)

    if not save_result.is_success:
        return to_http_response(save_result)

    response_chunks = [
        ProcessedChunkDTO(
            page_content=document.page_content,
            metadata=document.metadata,
        )
        for document in documents
    ]

    return to_http_response(
        Result.success(response_chunks),
        success_message="File processed and chunks saved successfully.",
    )



# Get one chunk


@data_router.get(
    "/chunks/{chunk_id}",
    response_model=ApiResponse[DataChunk],
)
async def get_chunk_by_id(
    chunk_id: str,
    chunk_bl: ChunkBL,
) -> JSONResponse:
    
    if not ObjectId.is_valid(chunk_id):
        # Replace this with your project's standard validation error.
        from src.helpers.result_pattern import ErrorType, ResultError

        return to_http_response(
            Result.failure(
                ResultError(
                    code="invalid_chunk_id",
                    message="Invalid chunk ID.",
                    type=ErrorType.VALIDATION,
                )
            )
        )

    result = await chunk_bl.get_chunk_by_id(ObjectId(chunk_id))

    return to_http_response(result)



# Get chunks for a project


@data_router.get(
    "/chunks/project/{project_id}",
    response_model=ApiResponse[list[DataChunk]],
)
async def get_chunks_by_project_id(
    project_id: str,
    chunk_bl: ChunkBL,
    page_size: int = Query(default=100, gt=0, le=1000),
    page_num: int = Query(default=1, gt=0),
) -> JSONResponse:
    if not ObjectId.is_valid(project_id):
        from src.helpers.result_pattern import ErrorType, ResultError

        return to_http_response(
            Result.failure(
                ResultError(
                    code="invalid_project_id",
                    message="Invalid project ID.",
                    type=ErrorType.VALIDATION,
                )
            )
        )

    result = await chunk_bl.get_chunks_by_project_id(
        project_id=ObjectId(project_id),
        page_size=page_size,
        page_num=page_num,
    )

    return to_http_response(result)



# Delete all chunks for a project


@data_router.delete(
    "/chunks/project/{project_id}",
    response_model=ApiResponse[int],
)
async def delete_chunks_by_project_id(
    project_id: str,
    chunk_bl: ChunkBL,
) -> JSONResponse:
    if not ObjectId.is_valid(project_id):
        from src.helpers.result_pattern import ErrorType, ResultError

        return to_http_response(
            Result.failure(
                ResultError(
                    code="invalid_project_id",
                    message="Invalid project ID.",
                    type=ErrorType.VALIDATION,
                )
            )
        )

    result = await chunk_bl.delete_by_project_id(ObjectId(project_id))

    return to_http_response(
        result,
        success_message="Project chunks deleted successfully.",
    )
