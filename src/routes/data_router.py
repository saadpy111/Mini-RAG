
from pathlib import Path
from typing import Annotated

from bson import ObjectId
from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import JSONResponse

from src.api import to_http_response
from src.business_logic.asset_business_logic import AssetBusinessLogic
from src.business_logic.chunk_business_logic import (
    ChunkBusinessLogic,
    build_data_chunks,
)
from src.business_logic.project_business_logic import ProjectBusinessLogic
from src.dependencies.dependency_injection import (
    get_asset_business_logic,
    get_chunk_business_logic,
    get_project_business_logic,
)
from src.dtos import (
    ApiResponse,
    ProcessedAssetDTO,
    ProcessedFileDTO,
    ProcessRequest,
    ProjectProcessRequest,
    ProjectProcessResultDTO,
    UploadFileDTO,
)
from src.helpers.result_pattern import Result, ResultError, ErrorType
from src.models.asset import Asset
from src.models.data_chunk import DataChunk
from src.models.project import Project
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

AssetBL = Annotated[
    AssetBusinessLogic,
    Depends(get_asset_business_logic),
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
    project_bl: ProjectBL,
    asset_bl: AssetBL,
    file: UploadFile = File(...),
) -> JSONResponse:
    # 1. Get the project or create it if it does not exist.
    project_result = await project_bl.get_project(project_id)

    if project_result.is_success:
        project = project_result.value

    elif project_result.error.type == ErrorType.NOT_FOUND:
        create_result = await project_bl.create_project(
            Project(project_id=project_id)
        )

        if not create_result.is_success:
            return to_http_response(create_result)

        project = create_result.value

    else:
        return to_http_response(project_result)

    # 2. Validate the uploaded file.
    validation_result = await validate_uploaded_file(file)

    if not validation_result.is_success:
        return to_http_response(validation_result)

    # 3. Upload the physical file.
    upload_result = await upload_file(project_id, file)

    if not upload_result.is_success:
        return to_http_response(upload_result)

    uploaded_file: UploadFileDTO = upload_result.value

    # 4. Get the actual stored file size.
    try:
        asset_size = Path(uploaded_file.file_path).stat().st_size
    except OSError:
        return to_http_response(
            Result.failure(
                ResultError(
                    code="uploaded_file_size_unavailable",
                    message="The uploaded file size could not be determined.",
                    type=ErrorType.INTERNAL,
                )
            )
        )

    # 5. Persist asset metadata.
    asset = Asset(
        asset_project_id=project.id,
        asset_type=Path(uploaded_file.original_filename).suffix.lower(),
        asset_name=uploaded_file.stored_filename,
        asset_size=asset_size,
        asset_config={
            "file_id": uploaded_file.file_id,
            "original_filename": uploaded_file.original_filename,
            "file_path": uploaded_file.file_path,
        },
    )

    asset_result = await asset_bl.create_asset(asset)

    if not asset_result.is_success:
        return to_http_response(asset_result)

    # 6. Return the existing upload DTO.
    return to_http_response(
        Result.success(uploaded_file),
        success_status_code=status.HTTP_201_CREATED,
        success_message="File uploaded and asset metadata saved successfully.",
    )

# Process and persist chunks


@data_router.post(
    "/process/{project_id}",
    response_model=ApiResponse[ProcessedFileDTO],
)
async def process_document(
    project_id: str,
    process_request: ProcessRequest,
    project_bl: ProjectBL,
    chunk_bl: ChunkBL,
    asset_bl: AssetBL,
) -> JSONResponse:
    request_result = validate_process_request(process_request)

    if not request_result.is_success:
        return to_http_response(request_result)

    project_result = await project_bl.get_project(project_id)

    if not project_result.is_success:
        return to_http_response(project_result)

    project = project_result.value

    asset_result = await asset_bl.get_asset_by_file_id(
        project_id=project.id,
        file_id=process_request.file_id,
    )

    if not asset_result.is_success:
        return to_http_response(asset_result)

    asset = asset_result.value

    if asset.id is None:
        return to_http_response(
            Result.failure(
                ResultError(
                    code="invalid_asset_id",
                    message="Asset identifier is missing.",
                    type=ErrorType.INTERNAL,
                )
            )
        )

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

    data_chunks = build_data_chunks(
        documents=documents,
        project_id=project.id,
        asset_id=asset.id,
    )

    save_result = await chunk_bl.insert_many_chunks(data_chunks)

    if not save_result.is_success:
        return to_http_response(save_result)

    persisted_count = save_result.value or 0

    processing_result = ProcessedFileDTO(
        project_id=project.project_id,
        asset_id=asset.id,
        file_id=process_request.file_id,
        is_success=True,
        total_chunks=persisted_count,
    )

    return to_http_response(
        Result.success(processing_result),
        success_message="File processed and chunks saved successfully.",
    )


# Process all project assets


def _failed_asset_outcome(
    asset_id: ObjectId | None,
    file_id: str | None,
    error: ResultError,
) -> ProcessedAssetDTO:
    return ProcessedAssetDTO(
        asset_id=asset_id,
        file_id=file_id,
        is_success=False,
        error_code=error.code,
        error_message=error.message,
    )


@data_router.post(
    "/process/project/{project_id}",
    response_model=ApiResponse[ProjectProcessResultDTO],
)
async def process_project_assets(
    project_id: str,
    project_bl: ProjectBL,
    asset_bl: AssetBL,
    chunk_bl: ChunkBL,
    process_request: ProjectProcessRequest | None = None,
) -> JSONResponse:
    project_result = await project_bl.get_project(project_id)

    if not project_result.is_success:
        return to_http_response(project_result)

    project = project_result.value

    if project.id is None:
        return to_http_response(
            Result.failure(
                ResultError(
                    code="invalid_project_id",
                    message="Project identifier is missing.",
                    type=ErrorType.INTERNAL,
                )
            )
        )

    assets_result = await asset_bl.get_all_assets_by_project_id(project.id)

    if not assets_result.is_success:
        return to_http_response(assets_result)

    assets = assets_result.value

    if not assets:
        return to_http_response(
            Result.failure(
                ResultError(
                    code="no_assets_in_project",
                    message="Project has no assets to process.",
                    type=ErrorType.UNPROCESSABLE,
                )
            )
        )

    options = process_request or ProjectProcessRequest()

    asset_outcomes: list[ProcessedAssetDTO] = []
    failures: list[ResultError] = []
    processed_assets = 0
    total_chunks = 0

    for asset in assets:
        file_id = asset.asset_config.get("file_id")

        if not isinstance(file_id, str) or not file_id.strip():
            error = ResultError(
                code="asset_metadata_missing",
                message=(
                    "Asset metadata does not contain a valid file identifier."
                ),
                type=ErrorType.UNPROCESSABLE,
            )
            failures.append(error)
            asset_outcomes.append(
                _failed_asset_outcome(asset.id, None, error)
            )
            continue

        if asset.id is None:
            error = ResultError(
                code="invalid_asset_id",
                message="Asset identifier is missing.",
                type=ErrorType.INTERNAL,
            )
            failures.append(error)
            asset_outcomes.append(
                _failed_asset_outcome(None, file_id, error)
            )
            continue

        file_content_result = get_file_content(
            project_id=project.project_id,
            file_id=file_id,
        )

        if not file_content_result.is_success:
            failures.append(file_content_result.error)
            asset_outcomes.append(
                _failed_asset_outcome(
                    asset.id,
                    file_id,
                    file_content_result.error,
                )
            )
            continue

        chunks_result = process_file_content(
            file_content=file_content_result.value,
            chunk_size=options.chunk_size,
            overlap_size=options.overlap_size,
        )

        if not chunks_result.is_success:
            failures.append(chunks_result.error)
            asset_outcomes.append(
                _failed_asset_outcome(
                    asset.id,
                    file_id,
                    chunks_result.error,
                )
            )
            continue

        data_chunks = build_data_chunks(
            documents=chunks_result.value,
            project_id=project.id,
            asset_id=asset.id,
        )

        save_result = await chunk_bl.replace_chunks_for_asset(
            project_id=project.id,
            asset_id=asset.id,
            chunks=data_chunks,
        )

        if not save_result.is_success:
            failures.append(save_result.error)
            asset_outcomes.append(
                _failed_asset_outcome(
                    asset.id,
                    file_id,
                    save_result.error,
                )
            )
            continue

        chunk_count = save_result.value or 0
        processed_assets += 1
        total_chunks += chunk_count
        asset_outcomes.append(
            ProcessedAssetDTO(
                asset_id=asset.id,
                file_id=file_id,
                is_success=True,
                chunk_count=chunk_count,
            )
        )

    failed_assets = len(assets) - processed_assets

    if processed_assets == 0:
        first_error = failures[0]
        message = first_error.message

        if len(failures) > 1:
            message = (
                f"{message} ({len(failures) - 1} more asset(s) failed.)"
            )

        return to_http_response(
            Result.failure(
                ResultError(
                    code=first_error.code,
                    message=message,
                    type=first_error.type,
                )
            )
        )

    result = ProjectProcessResultDTO(
        project_id=project.project_id,
        total_assets=len(assets),
        processed_assets=processed_assets,
        failed_assets=failed_assets,
        total_chunks=total_chunks,
        assets=asset_outcomes,
    )

    return to_http_response(
        Result.success(result),
        success_message=(
            f"Processed {processed_assets} of {len(assets)} asset(s); "
            f"{total_chunks} chunk(s) saved; {failed_assets} failed."
        ),
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
