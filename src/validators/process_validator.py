from src.dtos import ProcessRequest
from src.helpers.result_pattern import ErrorType, Result, ResultError


def validate_process_request(request: ProcessRequest) -> Result[None]:
    
    return Result.success(None)
