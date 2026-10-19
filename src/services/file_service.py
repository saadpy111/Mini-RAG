from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from src.dtos import UploadFileDTO
from src.helpers.config import settings
from src.helpers.result_pattern import ErrorType, Result, ResultError

ROOT_DIR = Path(__file__).resolve().parents[1]

UPLOAD_DIR = ROOT_DIR / "assets" / "files"
CHUNK_SIZE = settings.file_default_chunk_size


async def upload_file(
    file: UploadFile,
) -> Result[UploadFileDTO]:

    file_path = None

    try:
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

        original_filename = file.filename or ""
        extension = Path(original_filename).suffix.lower()

        stored_filename = f"{uuid4().hex}{extension}"
        file_path = UPLOAD_DIR / stored_filename

        with file_path.open("wb") as destination:
            while chunk := await file.read(CHUNK_SIZE):
                destination.write(chunk)

        dto = UploadFileDTO(
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_path=str(file_path),
        )

        return Result.success(dto)

    except OSError:
        if file_path is not None:
            file_path.unlink(missing_ok=True)

        return Result.failure(
            ResultError(
                code="file_storage_error",
                message="Failed to save the uploaded file.",
                type=ErrorType.INTERNAL,
            )
        )

    finally:
        await file.close()
