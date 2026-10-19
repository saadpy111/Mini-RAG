from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.api import to_http_response
from src.dtos import ApiResponse
from src.helpers import config
from src.helpers.result_pattern import Result

router = APIRouter(
    prefix="/api/v1",
    tags=["api_v1"],
)


@router.get(
    "/",
    response_model=ApiResponse[dict[str, str]],
)
async def read_root() -> JSONResponse:
    result = Result.success(
        {
            "APP_NAME": config.settings.app_name,
            "APP_VERSION": config.settings.app_version,
        }
    )

    return to_http_response(
        result,
        success_message="Application information retrieved successfully.",
    )
