from dataclasses import dataclass
from enum import Enum
from typing import Generic, TypeVar

from src.constants import ErrorCode, ErrorMessage

T = TypeVar("T")


class ErrorType(str, Enum):
    VALIDATION = "validation"
    BUSINESS_RULE = "business_rule"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    PAYLOAD_TOO_LARGE = "payload_too_large"
    UNPROCESSABLE = "unprocessable"
    INTERNAL = "internal"


@dataclass(frozen=True)
class ResultError:
    code: str
    message: str
    type: ErrorType = ErrorType.VALIDATION

    def __str__(self) -> str:
        return self.message


@dataclass(frozen=True)
class Result(Generic[T]):
    is_success: bool
    value: T | None = None
    error: ResultError | None = None

    def __post_init__(self) -> None:
        if self.is_success:
            if self.error is not None:
                raise ValueError(ErrorMessage.SUCCESS_CANNOT_CONTAIN_ERROR)
            return

        if self.error is None:
            raise ValueError(ErrorMessage.FAILURE_REQUIRES_ERROR)
        if self.value is not None:
            raise ValueError(ErrorMessage.FAILURE_CANNOT_CONTAIN_VALUE)

    @classmethod
    def success(cls, value: T) -> "Result[T]":
        return cls(is_success=True, value=value)

    @classmethod
    def failure(
        cls,
        error: ResultError | str,
        error_type: ErrorType = ErrorType.VALIDATION,
    ) -> "Result[T]":
        if isinstance(error, str):
            error = ResultError(
                code=ErrorCode.FALLBACK,
                message=error,
                type=error_type,
            )

        return cls(is_success=False, error=error)
