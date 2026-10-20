import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.dtos import ApiResponse

logger = logging.getLogger(__name__)

VALIDATION_ERROR_MESSAGE = "Request validation failed."
HTTP_ERROR_MESSAGE = "Request failed."
INTERNAL_ERROR_MESSAGE = "An internal server error occurred."


async def request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    body = ApiResponse[None](
        is_success=False,
        message=VALIDATION_ERROR_MESSAGE,
        data=None,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=body.model_dump(mode="json"),
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else HTTP_ERROR_MESSAGE
    body = ApiResponse[None](
        is_success=False,
        message=message,
        data=None,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=body.model_dump(mode="json"),
        headers=exc.headers,
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    logger.error(
        "Unhandled exception while processing request.",
        exc_info=exc,
    )
    body = ApiResponse[None](
        is_success=False,
        message=INTERNAL_ERROR_MESSAGE,
        data=None,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=body.model_dump(mode="json"),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(
        RequestValidationError,
        request_validation_exception_handler,
    )
    app.add_exception_handler(
        StarletteHTTPException,
        http_exception_handler,
    )
    app.add_exception_handler(Exception, unhandled_exception_handler)
