from fastapi import APIRouter, File, UploadFile, status
from fastapi.responses import JSONResponse

from src.api import to_http_response
from src.dtos import ApiResponse, UploadFileDTO
from src.services.file_service import upload_file
from src.validators.file_validator import validate_uploaded_file

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
async def upload_document(project_id : str,file: UploadFile = File(...)) -> JSONResponse:

    # 1. Validate the uploaded file
    validation_result = await validate_uploaded_file(file)

    if not validation_result.is_success:
        return to_http_response(validation_result)

    # 2. Save the file
    result = await upload_file(project_id,file)

    # 3. Return successful or failed response
    return to_http_response(
        result,
        success_status_code=status.HTTP_201_CREATED,
        success_message="File uploaded successfully.",
    )
