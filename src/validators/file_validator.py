from pathlib import Path

from fastapi import UploadFile

from src.helpers.config import settings
from src.helpers.result_pattern import ErrorType, Result, ResultError


async def validate_uploaded_file(
    file: UploadFile,
) -> Result[str]:

    # 1. Validate filename
    if not file.filename:
        return Result.failure(
            ResultError(
                code="missing_filename",
                message="Filename is required.",
                type=ErrorType.VALIDATION,
            )
        )

    # 2. Validate extension
    extension = Path(file.filename).suffix.lower()

    if extension not in settings.file_allowed_types:
        return Result.failure(
            ResultError(
                code="unsupported_file_type",
                message=(
                    "File type not allowed. Allowed types: "
                    f"{', '.join(settings.file_allowed_types)}"
                ),
                type=ErrorType.VALIDATION,
            )
        )

    # 3. Validate file size
    max_size_bytes = settings.file_max_size * 1024 * 1024

    content = await file.read(max_size_bytes + 1)

    if len(content) > max_size_bytes:
        await file.seek(0)
        return Result.failure(
            ResultError(
                code="file_too_large",
                message=(
                    f"File size exceeds the limit of "
                    f"{settings.file_max_size} MB."
                ),
                type=ErrorType.PAYLOAD_TOO_LARGE,
            )
        )

    # Reset file pointer
    await file.seek(0)

    return Result.success(extension)
