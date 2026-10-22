from pathlib import Path

from src.helpers.result_pattern import ErrorType, Result, ResultError


def get_base_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def get_files_dir() -> Path:
    return get_base_dir() / "assets" / "files"


def _validate_project_id(project_id: str) -> ResultError | None:
    if (
        not project_id
        or project_id in {".", ".."}
        or Path(project_id).name != project_id
    ):
        return ResultError(
            code="invalid_project_id",
            message="Invalid project ID.",
            type=ErrorType.VALIDATION,
        )

    return None


def get_project_dir(project_id: str) -> Result[Path]:
    validation_error = _validate_project_id(project_id)
    if validation_error is not None:
        return Result.failure(validation_error)

    return Result.success(get_files_dir() / project_id)


def get_project_path(project_id: str) -> Result[Path]:
    project_dir_result = get_project_dir(project_id)
    if not project_dir_result.is_success:
        return project_dir_result

    project_dir = project_dir_result.value
    if not project_dir.is_dir():
        return Result.failure(
            ResultError(
                code="project_not_found",
                message=f"Project '{project_id}' was not found.",
                type=ErrorType.NOT_FOUND,
            )
        )

    return Result.success(project_dir)
