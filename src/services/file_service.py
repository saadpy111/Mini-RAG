from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from src.dtos import UploadFileDTO
from src.helpers.config import settings
from src.helpers.result_pattern import ErrorType, Result, ResultError
from src.services.project_service import get_project_dir

CHUNK_SIZE = settings.file_default_chunk_size


async def upload_file(
    project_id: str,
    file: UploadFile,
) -> Result[UploadFileDTO]:
    file_path = None

    try:
        project_dir_result = get_project_dir(project_id)
        if not project_dir_result.is_success:
            return project_dir_result

        upload_dir = project_dir_result.value
        upload_dir.mkdir(parents=True, exist_ok=True)

        original_filename = file.filename or ""
        extension = Path(original_filename).suffix.lower()
        file_id = uuid4().hex
        stored_filename = f"{file_id}{extension}"
        file_path = upload_dir / stored_filename

        with file_path.open("wb") as destination:
            while chunk := await file.read(CHUNK_SIZE):
                destination.write(chunk)

        dto = UploadFileDTO(
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_id=file_id,
            file_path=str(file_path),
        )

        return Result.success(dto)

    except OSError:
        if file_path is not None:
            try:
                file_path.unlink(missing_ok=True)
            except OSError:
                pass

        return Result.failure(
            ResultError(
                code="file_storage_error",
                message="Failed to save the uploaded file.",
                type=ErrorType.INTERNAL,
            )
        )

    finally:
        await file.close()
