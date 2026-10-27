from typing import TypeVar

from fastapi import status
from fastapi.responses import JSONResponse

from src.constants import ErrorMessage, SuccessMessage
from src.dtos import ApiResponse
from src.helpers.result_pattern import ErrorType, Result

T = TypeVar("T")

ERROR_STATUS_CODES: dict[ErrorType, int] = {
    ErrorType.VALIDATION: status.HTTP_400_BAD_REQUEST,
    ErrorType.NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ErrorType.BUSINESS_RULE: status.HTTP_400_BAD_REQUEST,
    ErrorType.CONFLICT: status.HTTP_409_CONFLICT,
    ErrorType.PAYLOAD_TOO_LARGE: status.HTTP_413_CONTENT_TOO_LARGE,
    ErrorType.UNPROCESSABLE: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ErrorType.INTERNAL: status.HTTP_500_INTERNAL_SERVER_ERROR,
}

DEFAULT_SUCCESS_STATUS = status.HTTP_200_OK
DEFAULT_SUCCESS_MESSAGE = SuccessMessage.OPERATION_COMPLETED
INTERNAL_ERROR_STATUS = status.HTTP_500_INTERNAL_SERVER_ERROR


def to_http_response(
    result: Result[T],
    *,
    success_status_code: int = DEFAULT_SUCCESS_STATUS,
    success_message: str = DEFAULT_SUCCESS_MESSAGE,
) -> JSONResponse:
    if result.is_success:
        body = ApiResponse[T](
            is_success=True,
            message=success_message,
            data=result.value,
        )
        return JSONResponse(
            status_code=success_status_code,
            content=body.model_dump(mode="json"),
        )

    error = result.error
    if error is None:
        raise ValueError(ErrorMessage.FAILURE_REQUIRES_ERROR)

    body = ApiResponse[None](
        is_success=False,
        message=error.message,
        data=None,
    )
    return JSONResponse(
        status_code=ERROR_STATUS_CODES.get(error.type, INTERNAL_ERROR_STATUS),
        content=body.model_dump(mode="json"),
    )
