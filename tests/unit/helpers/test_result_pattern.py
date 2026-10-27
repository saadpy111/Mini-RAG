import pytest

from src.helpers.result_pattern import ErrorType, Result, ResultError


def test_success_result_holds_value():
    result = Result.success(42)

    assert result.is_success is True
    assert result.value == 42
    assert result.error is None


def test_failure_result_holds_error():
    error = ResultError(
        code="not_found",
        message="Resource not found.",
        type=ErrorType.NOT_FOUND,
    )

    result = Result.failure(error)

    assert result.is_success is False
    assert result.value is None
    assert result.error is error


def test_failure_accepts_plain_message():
    result = Result.failure(
        "Something went wrong.",
        error_type=ErrorType.BUSINESS_RULE,
    )

    assert result.error.code == "error"
    assert result.error.message == "Something went wrong."
    assert result.error.type is ErrorType.BUSINESS_RULE


def test_failure_defaults_to_validation_error_type():
    result = Result.failure("Invalid input.")

    assert result.error.type is ErrorType.VALIDATION


def test_result_error_string_is_its_message():
    error = ResultError(
        code="file_not_found",
        message="File was not found.",
        type=ErrorType.NOT_FOUND,
    )

    assert str(error) == "File was not found."


def test_success_cannot_contain_error():
    with pytest.raises(ValueError):
        Result(
            is_success=True,
            value=1,
            error=ResultError(code="boom", message="Boom."),
        )


def test_failure_requires_error():
    with pytest.raises(ValueError):
        Result(is_success=False, value=None, error=None)


def test_failure_cannot_contain_value():
    with pytest.raises(ValueError):
        Result(
            is_success=False,
            value=1,
            error=ResultError(code="boom", message="Boom."),
        )
