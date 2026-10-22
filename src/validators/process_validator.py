from src.dtos import ProcessRequest
from src.helpers.result_pattern import ErrorType, Result, ResultError


def validate_process_request(request: ProcessRequest) -> Result[None]:
    if request.do_reset:
        return Result.failure(
            ResultError(
                code="reset_not_supported",
                message="Reset is not supported.",
                type=ErrorType.UNPROCESSABLE,
            )
        )

    return Result.success(None)
